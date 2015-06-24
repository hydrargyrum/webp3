#!/usr/bin/env python
# license: You can redistribute this file and/or modify it under the terms of the WTFPLv2 [see sys/COPYING.WTFPL]

import BaseHTTPServer
import SocketServer
import os
import re
import hashlib
import urllib
import urlparse
import subprocess
import argparse
import zipfile
import tempfile
import select
import mako.template

PORT = 8000
ROOTS = {}
MATCH_ETAG = True
AUDIO_EXTENSIONS = {'.flac': 'audio/flac', '.ogg': 'audio/ogg', '.mp3': 'audio/mpeg', '.wav': 'audio/x-wav', '.m4a': 'audio/mpeg'}
OGGENCODE = False
ZIPPING = False
SYSPATH = os.path.join(os.path.dirname(__file__), 'sys')
QUIT = False

class NotFound(Exception):
	pass


class Forbidden(Exception):
	pass


def natural_sort_ci(l):
	def try_int(v):
		try:
			return int(v)
		except ValueError:
			return v

	def natural_sort_ci_key(k):
		return map(try_int, re.findall(r'\d+|\D+', k.lower()))

	l.sort(key=natural_sort_ci_key)

def gen_etag(*data, **kw):
	if kw.get('is_file', False):
		data = (data, os.stat(data[0]))
	t = hashlib.new('md5', repr(data)).hexdigest()
	if kw.get('weak', True):
		return 'W/"%s"' % t
	else:
		return '"%s"' % t

def is_audio(name):
	return any(name.endswith(ext) for ext in AUDIO_EXTENSIONS)

def decode_u8(s):
	return s.decode('utf-8')

def mime(path):
	for ext in AUDIO_EXTENSIONS:
		if path.endswith(ext):
			return AUDIO_EXTENSIONS[ext]
	return ''

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


class ThreadedServer(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
	pass


class AudioRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
	template_name = os.path.join(SYSPATH, 'base.tpl')

	def _write_body(self, s):
		if self.command == 'HEAD':
			return

		if not self.range:
			self.wfile.write(s)
		else:
			self.wfile.write(s[self.range[0]:self.range[1]])

	def _write_fd(self, f, outfd):
		if self.command == 'HEAD':
			return

		if self.range:
			f.seek(self.range[0])

		while True:
			if self.range:
				buflen = min(select.PIPE_BUF, self.range[1] - f.tell())
			else:
				buflen = select.PIPE_BUF
			buf = f.read(buflen)
			if not buf:
				break
			while True:
				_, o, _ = select.select([], [outfd], [], .5)
				if QUIT:
					outfd.close()
					return
				elif o:
					outfd.write(buf)
					break

	def _write_file(self, filename, outfd):
		if self.command == 'HEAD':
			return

		with file(filename, 'rb') as f:
			self._write_fd(f, outfd)

	def matches_etag(self, etag):
		# returns True if caller should stop processing the request
		if not MATCH_ETAG:
			return False

		if etag in self.headers.get('If-None-Match', ''):
			self.send_response(304)
			self.send_header('ETag', etag)
			self.end_headers()
			return True
		return False

	def handle_partial(self, size):
		# returns True if caller should stop processing the request
		self.range = None
		header = self.headers.get('Range')
		if not header:
			self.send_response(200)
			self.send_header('Content-Length', size)
			return False

		if not header.startswith('bytes='):
			self.send_error(400)

		ranges = header[6:].split(',')
		if len(ranges) != 1:
			self.send_error(400)
			return True

		r = ranges[0].split('-')
		if len(r) != 2:
			self.send_error(400)
			return True
		start = int(r[0])
		end = size - 1
		if r[1]:
			end = min(size - 1, int(r[1]))
		if start >= size:
			self.send_error(416)
			return True

		self.send_response(206)
		self.send_header('Content-Range', '%s-%s/%s' % (start, end, size))
		self.send_header('Content-Length', end - start + 1)
		self.range = (start, end + 1)
		return False

	def extract_url_path(self):
		_, _, path, _, query, _ = urlparse.urlparse(self.path)
		params = urlparse.parse_qs(query)
		path = urllib.unquote_plus(path).decode('utf-8')
		return path, params

	def resolve_user_path(self, path):
		if not path: # url = /
			return None
		try:
			rootname, subpath = path.split('/', 1)
		except ValueError: # url = /foo
			rootname, subpath = path, ''
		try:
			ret = ROOTS[rootname]
		except KeyError:
			raise NotFound()
		if subpath: # url = /foo/bar...
			ret = os.path.join(ret, subpath)

		if not os.path.exists(ret):
			raise NotFound()
		return ret

	def do_GET(self):
		urlpath, params = self.extract_url_path()
		try:
			path = norm(urlpath)
		except Forbidden:
			return self.do_forbidden()

		if path.startswith('_/'):
			return self.do_sysfile(path)

		try:
			userpath = self.resolve_user_path(path)
		except NotFound:
			return self.do_notfound()
		except Forbidden:
			return self.do_forbidden()

		if userpath is None:
			return self.do_list_root(params)
		elif os.path.isdir(userpath):
			if not urlpath.endswith('/'):
				return self.redirect_slash(urlpath)
			return self.do_dir(userpath, params)
		elif os.path.isfile(userpath):
			return self.do_file(userpath, params)
		else:
			return self.do_notfound()

	do_HEAD = do_GET

	def redirect_slash(self, urlpath):
		urlpath = urlpath + '/'

		self.send_response(302)
		self.send_header('Location', urlpath)
		self.send_header('Content-Length', 0)
		self.end_headers()

	def do_notfound(self):
		self.send_error(404)

	def do_forbidden(self):
		self.send_error(403)

	def do_sysfile(self, path):
		if path.startswith('_/'):
			path = path[2:]

		path = os.path.join(SYSPATH, path)
		if not os.path.isfile(path):
			return self.do_notfound()

		etag = gen_etag(path, is_file=True, weak=False)
		if self.matches_etag(etag):
			return

		if self.handle_partial(os.path.getsize(path)):
			return

		self.send_header('ETag', etag)
		self.end_headers()
		self._write_file(path, self.wfile)

	def do_file(self, path, params=None):
		etag = gen_etag(path, params, is_file=True, weak=bool(params))
		if self.matches_etag(etag):
			return

		if not params or not params.get('convert') or not OGGENCODE:
			return self.do_send_file(path, etag)

		if params.get('convert') == ['ogg']:
			self.send_response(200)
			self.send_header('Content-Type', 'audio/ogg')
			self.send_header('ETag', etag)
			self.end_headers()
			subprocess.call(['sox', path, '-t', 'ogg', '-'], stdout=self.wfile)

	def do_send_file(self, path, etag):
		if self.handle_partial(os.path.getsize(path)):
			return

		self.send_header('Content-Type', mime(path))
		self.send_header('ETag', etag)
		self.end_headers()
		self._write_file(path, self.wfile)

	def do_zip(self, path):
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

	def do_dir(self, path, params=None):
		files = os.listdir(path)
		natural_sort_ci(files)

		etag = gen_etag(self.template_name, params, path, files, is_file=True, weak=True)
		if self.matches_etag(etag):
			return

		if params and params.get('zip') and ZIPPING:
			return self.do_zip(path)

		items = [self.make_item_data(os.path.join(path, f)) for f in files]
		items.sort(key=lambda i: not i['is_dir']) # dirs first
		files = [i['basename'] for i in items if is_audio(i['basename'])]

		relpath, _ = self.extract_url_path()
		self.template = mako.template.Template(filename=self.template_name)
		body = self.template.render(items=items, files=files, relpath=relpath, parent=parent).encode('utf-8')

		if self.handle_partial(len(body)):
			return
		self.send_header('Content-Type', 'text/html')
		self.send_header('ETag', etag)
		self.end_headers()
		self._write_body(body)

	def do_list_root(self, params=None):
		items = [dict(size=0, basename=k, is_dir=True, is_audio=False) for k in ROOTS.keys()]
		items.sort(key=lambda x: x['basename'])

		etag = gen_etag(ROOTS, weak=True)
		if self.matches_etag(etag):
			return

		self.template = mako.template.Template(filename=self.template_name)
		body = self.template.render(items=items, files=[], relpath='/', parent='/').encode('utf-8')

		if self.handle_partial(len(body)):
			return
		self.send_header('Content-Type', 'text/html')
		self.send_header('ETag', etag)
		self.end_headers()
		self._write_body(body)

	def make_item_data(self, path):
		basename = os.path.basename(path)
		return dict(size=os.path.getsize(path), basename=basename, is_dir=os.path.isdir(path), is_audio=is_audio(basename))


def run(server_class=BaseHTTPServer.HTTPServer, handler_class=BaseHTTPServer.BaseHTTPRequestHandler):
	server_address = ('', PORT)
	httpd = server_class(server_address, handler_class)
	httpd.serve_forever()


def main():
	global PORT, OGGENCODE, ZIPPING, ROOTS, QUIT

	parser = argparse.ArgumentParser()
	parser.add_argument('folders', metavar='NAME=PATH', nargs='+', help='give access to PATH under /NAME/')
	parser.add_argument('-p', '--port', metavar='PORT', default=8000, type=int, help='listen on PORT')
	parser.add_argument('--encode', action='store_true', help='support reencoding non-ogg to ogg (cpu intensive on server)')
	parser.add_argument('--zip', action='store_true', help='support zipping directories (space consuming on server)')
	args = parser.parse_args()

	OGGENCODE = args.encode
	ZIPPING = args.zip
	PORT = args.port
	ROOTS = {}
	for fstr in args.folders:
		fdata = fstr.split('=', 1)
		if len(fdata) != 2 or not all(fdata):
			parser.error('folders must be with format NAME=PATH')
		key = decode_u8(fdata[0])
		if key in ROOTS:
			parser.error('roots can only be specified once: %s' % key)
		ROOTS[key] = decode_u8(fdata[1])

	try:
		run(server_class=ThreadedServer, handler_class=AudioRequestHandler)
	except KeyboardInterrupt:
		QUIT = True

if __name__ == '__main__':
	main()
