#!/usr/bin/env python3
# license: You can redistribute this file and/or modify it under the terms of the WTFPLv2 [see COPYING.WTFPL]

from functools import wraps
import errno
import os
import re
import hashlib
import json
import mimetypes
import subprocess
import tempfile
import threading
import zipfile

from bottle import route, request, response, redirect, abort, mako_template, static_file


ROOTS = {}
MATCH_ETAG = True
AUDIO_EXTENSIONS = {'.flac': 'audio/flac', '.ogg': 'audio/ogg', '.mp3': 'audio/mpeg', '.wav': 'audio/x-wav', '.m4a': 'audio/mpeg'}
CAN_OGGENCODE = False
CAN_ZIP = False
CURRENT_ZIPPING = threading.Semaphore(2) # limit DoS
SYSPATH = os.path.join(os.path.dirname(__file__), 'static')
TEMPLATE = os.path.join(SYSPATH, 'base.tpl')


class Forbidden(Exception):
	pass


def natural_sort_ci(l):
	def try_int(v):
		try:
			# force ints < strs
			return (0, int(v))
		except ValueError:
			return (1, v)

	def natural_sort_ci_key(k):
		return list(map(try_int, re.findall(r'\d+|\D+', k.lower())))

	l.sort(key=natural_sort_ci_key)


def gen_etag(*data, **kw):
	if kw.get('is_file', False):
		data = (data, os.stat(data[0]))
	t = hashlib.new('md5', repr(data).encode('utf-8')).hexdigest()
	if kw.get('weak', True):
		return 'W/"%s"' % t
	else:
		return '"%s"' % t


def is_audio(name):
	return any(name.endswith(ext) for ext in AUDIO_EXTENSIONS)


def get_mime(path):
	for ext in AUDIO_EXTENSIONS:
		if path.endswith(ext):
			return AUDIO_EXTENSIONS[ext]
	return mimetypes.guess_type(path)[0]


def parent(s):
	'''
	>>> parent('/foo/bar')
	'/foo'
	>>> parent('/foo/bar/')
	'/foo'
	'''

	if s.endswith('/'):
		s = s[:-1]
	return os.path.dirname(s)

def norm(path):
	'''
	>>> norm('/foo/../bar//')
	'bar'
	>>> norm('foo/bar/')
	'foo/bar'
	# norm('foo/../..') will raise Forbidden
	'''

	path = os.path.normpath(path)
	if path.startswith('/'):
		path = path[1:]
	if path.startswith('../'):
		raise Forbidden()
	return path


def handle_oserror(func):
	@wraps(func)
	def decorator(*args, **kwargs):
		try:
			return func(*args, **kwargs)
		except OSError as err:
			if err.errno == errno.ENOENT:
				abort(404, 'Not found')
			elif err.errno == errno.EACCES:
				abort(403, 'Forbidden')
			else:
				raise

	return decorator


class AudioRequestHandler(object):
	def do_file(self, path, params=None):
		etag = gen_etag(path, params, is_file=True, weak=bool(params))
		if self.matches_etag(etag):
			return

		if not params or not params.get('convert') or not CAN_OGGENCODE:
			return self.do_send_file(path, etag)

		if params.get('convert') == ['ogg']:
			self.send_response(200)
			self.send_header('Content-Type', 'audio/ogg')
			self.send_header('ETag', etag)
			self.end_headers()
			subprocess.call(['sox', path, '-t', 'ogg', '-'], stdout=self.wfile)

	def do_zip(self, path):
		if not CURRENT_ZIPPING.acquire(False):
			self.send_error(429, 'Too many operations in progress')
			return
		try:
			return self._do_zip(path)
		finally:
			CURRENT_ZIPPING.release()

	def _do_zip(self, path):
		with tempfile.TemporaryFile() as fd:
			with zipfile.ZipFile(fd, 'w') as zip:
				files = os.listdir(path)
				natural_sort_ci(files)
				for entry in files:
					absentry = os.path.join(path, entry)
					if os.path.isfile(absentry):
						zip.write(absentry, entry)
			size = fd.tell()
			fd.seek(0)

			if self.handle_partial(size):
				return
			self.send_header('Content-Disposition', 'attachment; filename="%s.zip"' % os.path.basename(path).encode('utf-8'))
			self.send_header('Content-Type', 'application/zip')
			self.end_headers()
			self._write_fd(fd, self.wfile)

	def make_item_data(self, path):
		basename = os.path.basename(path)
		return dict(size=os.path.getsize(path), basename=basename, is_dir=os.path.isdir(path), is_audio=is_audio(basename))


def _do_etag(etag):
	if not MATCH_ETAG:
		return

	response.headers['ETag'] = etag
	if etag in request.headers.get('If-None-Match', ''):
		abort(304, 'Not modified')


def _do_partial(size):
	# returns True if caller should stop processing the request
	res = None
	header = request.headers.get('Range')
	if not header:
		response.status = 200
		response.headers['Content-Length'] = size
		return None

	if not header.startswith('bytes='):
		abort(400, 'Bad request')

	ranges = header[6:].split(',')
	if len(ranges) != 1:
		abort(400, 'Bad request')

	r = ranges[0].split('-')
	if len(r) != 2:
		abort(400, 'Bad request')
	start = int(r[0])
	end = size - 1
	if r[1]:
		end = min(size - 1, int(r[1]))
	if start >= size:
		abort(416, 'Requested range not satisfiable')

	response.status = 206
	response.headers['Content-Range'] = '%s-%s/%s' % (start, end, size)
	response.headers['Content-Length'] = end - start + 1
	res = (start, end + 1)
	return res


def resolve_path(tree, path):
	if tree not in ROOTS:
		abort(404, 'Not found')

	try:
		path = norm(path)
	except Forbidden:
		abort(403, 'Forbidden')

	root = ROOTS[tree]
	res = os.path.join(root, path)

	if not os.path.exists(res):
		abort(404, 'Not found')

	return res


def make_item_data(path):
	basename = os.path.basename(path)
	return dict(size=os.path.getsize(path), basename=basename, is_dir=os.path.isdir(path), is_audio=is_audio(basename))


def is_json_request():
	# very rough parsing, to be improved if necessary
	header = request.headers['accept']
	return 'application/json' in re.split('[,;]', header)


@handle_oserror
def ls_dir(path, urlpath):
	files = os.listdir(path)

	natural_sort_ci(files)

	etag = gen_etag(path, files, is_file=True, weak=True)
	_do_etag(etag)

	#~ if params and params.get('zip') and CAN_ZIP:
		#~ return self.do_zip(path)

	items = [make_item_data(os.path.join(path, f)) for f in files]
	items.sort(key=lambda i: not i['is_dir']) # dirs first
	files = [i['basename'] for i in items if is_audio(i['basename'])]

	if is_json_request():
		response.headers['Content-Type'] = 'application/json'
		body = json.dumps(items)
	else:
		response.headers['Content-Type'] = 'text/html'
		body = mako_template(TEMPLATE, items=items, files=files, relpath=urlpath, parent=parent).encode('utf-8')

	#~ if self.handle_partial(len(body)):
		#~ return
	#~ self.send_header('ETag', etag)
	return body


@route('/')
def ls_root():
	items = [dict(size=0, basename=k, is_dir=True, is_audio=False) for k in ROOTS.keys()]
	items.sort(key=lambda x: x['basename'])

	etag = gen_etag(ROOTS.keys(), weak=True)
	_do_etag(etag)

	if is_json_request():
		response.headers['Content-Type'] = 'application/json'
		body = json.dumps(items)
	else:
		response.headers['Content-Type'] = 'text/html'
		body = mako_template(TEMPLATE, items=items, files=[], relpath='/', parent='/').encode('utf-8')

	range = _do_partial(len(body))
	if range:
		return body[range[0]:range[1]]
	else:
		return body


@route('/favicon.png')
def _static_favicon():
	return get_static('favicon.png')


@route('/robots.txt')
def _static_robots():
	return get_static('robots.txt')


@route('/_/<name>')
@handle_oserror
def get_static(name):
	return static_file(name, root='static')


@route('/<path:path>/_/<name>')
def get_static_sub(path, name):
	return get_static(name)


@route('/<tree>')
def ls_tree(tree):
	redirect(u'%s/' % tree)


@route('/<tree>/')
def ls_tree_trailing(tree):
	if tree not in ROOTS:
		abort(404, 'Not found')

	path = ROOTS[tree]
	return ls_dir(path, u'/%s' % tree)


@handle_oserror
def get_file(path):
	etag = gen_etag(path, is_file=True, weak=False)
	_do_etag(etag)

	mime = get_mime(path)
	if mime:
		response.headers['Content-Type'] = mime

	range = _do_partial(os.path.getsize(path))
	pos = 0

	with open(path, 'rb') as fd:
		if range:
			fd.seek(range[0])
			pos, end = range

		while (not range) or (pos < end):
			data = fd.read(1024)
			if not data:
				break
			if range:
				data = data[:end - pos]
			pos += len(data)
			yield data


@route('/<tree>/<path:path>')
def get_any(tree, path):
	if not path:
		return ls_tree(tree)

	dest = resolve_path(tree, path)
	if os.path.isfile(dest):
		return get_file(dest)
	elif os.path.isdir(dest):
		if not path.endswith('/'):
			last = os.path.basename(path)
			redirect(u'%s/' % last)
		return ls_dir(dest, u'/%s/%s' % (tree, path))
	else:
		abort(403, 'Forbidden')
