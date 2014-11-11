#!/usr/bin/env python
# license: do What The Fuck you want Public License version 2

import BaseHTTPServer
import SocketServer
import os
import re
import shutil
import hashlib
import urllib
import urlparse
import subprocess
import argparse
import mako.template

PORT = 8000
ROOTS = {}
MATCH_ETAG = True
AUDIO_EXTENSIONS = {'.flac': 'audio/flac', '.ogg': 'audio/ogg', '.mp3': 'audio/mpeg', '.wav': 'audio/x-wav', '.m4a': 'audio/mpeg'}
OGGENCODE = False
SYSPATH = 'sys'


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


class ThreadedServer(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
	pass


class AudioRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
	template_name = 'base'

	def matches_etag(self, etag):
		if not MATCH_ETAG:
			return False

		if etag in self.headers.get('If-None-Match', ''):
			self.send_response(304)
			self.send_header('ETag', etag)
			self.end_headers()
			return True
		return False

	def extract_url_path(self):
		_, _, path, _, query, _ = urlparse.urlparse(self.path)
		params = urlparse.parse_qs(query)
		path = urllib.unquote(path).decode('utf-8')
		return path, params

	def resolve_path(self, p):
		p = os.path.normpath(p)
		if '..' in p: # TODO improve
			raise Forbidden()
		if p.startswith('/'):
			p = p[1:]

		ps = p.split('/', 1)
		if len(ps) == 1 and not ps[0]: # /
			return None
		try: # /foo
			ret = ROOTS[ps[0]]
		except KeyError:
			raise NotFound()
		if len(ps) == 2: # /foo/bar
			ret = os.path.join(ret, ps[1])

		if not os.path.exists(ret):
			raise NotFound()
		return ret

	def do_GET(self):
		path, params = self.extract_url_path()

		if path.startswith('/_/'):
			return self.sysget(path)

		try:
			realpath = self.resolve_path(path)
		except NotFound:
			return self.do_notfound()
		except Forbidden:
			return self.do_forbidden()

		if realpath is None:
			return self.listroot(params)
		elif os.path.isdir(realpath):
			if not path.endswith('/'):
				return self.redirect_slash()
			return self.listdir(realpath, params)
		elif os.path.isfile(realpath):
			return self.handle_file(realpath, params)
		else:
			return self.handle_notfound()

	def redirect_slash(self):
		p = self.path
		if '?' not in p:
			p = p + '/'

		self.send_response(302)
		self.send_header('Location', p)
		self.send_header('Content-Length', 0)
		self.end_headers()

	def do_notfound(self):
		self.send_error(404)

	def do_forbidden(self):
		self.send_error(403)

	def mime(self, path):
		if path.endswith('.mp3'):
			return 'audio/mp3'
		elif path.endswith('.ogg'):
			return 'audio/ogg'
		else:
			return ''

	def sysget(self, path):
		path = os.path.normpath(path).replace('/_/', '')
		if '..' in path:
			return self.do_forbidden()

		path = os.path.join(SYSPATH, path)
		if not os.path.isfile(path):
			return self.do_notfound()

		etag = gen_etag(path, is_file=True, weak=False)
		if self.matches_etag(etag):
			return

		self.send_response(200)
		self.send_header('Content-Length', os.path.getsize(path))
		self.send_header('ETag', etag)
		self.end_headers()
		shutil.copyfileobj(open(path), self.wfile)

	def handle_file(self, path, params=None):
		etag = gen_etag(path, params, is_file=True, weak=bool(params))
		if self.matches_etag(etag):
			return

		if not params or not params.get('convert') or not OGGENCODE:
			return self.send_file(path, etag)

		if params.get('convert') == ['ogg']:
			self.send_response(200)
			self.send_header('Content-Type', 'audio/ogg')
			self.send_header('ETag', etag)
			self.end_headers()
			subprocess.call(['sox', path, '-t', 'ogg', '-'], stdout=self.wfile)

	def send_file(self, path, etag):
		with file(path, 'rb') as f:
			self.send_response(200)
			self.send_header('Content-Type', self.mime(path))
			self.send_header('Content-Length', os.path.getsize(path))
			self.send_header('ETag', etag)
			self.end_headers()
			shutil.copyfileobj(f, self.wfile)

	def listdir(self, path, params=None):
		files = os.listdir(path)
		natural_sort_ci(files)

		etag = gen_etag('sys/%s.tpl' % self.template_name, path, files, is_file=True, weak=True)
		if self.matches_etag(etag):
			return

		items = [self.make_item_data(os.path.join(path, f)) for f in files]
		items.sort(key=lambda i: not i['is_dir']) # dirs first
		files = [i['basename'] for i in items if is_audio(i['basename'])]

		relpath, _ = self.extract_url_path()
		self.template = mako.template.Template(filename='sys/%s.tpl' % self.template_name)
		body = self.template.render(items=items, files=files, relpath=relpath, parent=parent).encode('utf-8')

		self.send_response(200)
		self.send_header('Content-Length', len(body))
		self.send_header('Content-Type', 'text/html')
		self.send_header('ETag', etag)
		self.end_headers()
		self.wfile.write(body)

	def listroot(self, params=None):
		items = [dict(size=0, basename=k, is_dir=True, is_audio=False) for k in ROOTS.keys()]
		items.sort(key=lambda x: x['basename'])

		etag = gen_etag(ROOTS, weak=True)
		if self.matches_etag(etag):
			return

		self.template = mako.template.Template(filename='sys/%s.tpl' % self.template_name)
		body = self.template.render(items=items, files=[], relpath='/', parent='/').encode('utf-8')

		self.send_response(200)
		self.send_header('Content-Length', len(body))
		self.send_header('Content-Type', 'text/html')
		self.send_header('ETag', etag)
		self.end_headers()
		self.wfile.write(body)		

	def make_item_data(self, path):
		basename = os.path.basename(path)
		return dict(size=os.path.getsize(path), basename=basename, is_dir=os.path.isdir(path), is_audio=is_audio(basename))


def run(server_class=BaseHTTPServer.HTTPServer, handler_class=BaseHTTPServer.BaseHTTPRequestHandler):
	server_address = ('', PORT)
	httpd = server_class(server_address, handler_class)
	httpd.serve_forever()


def main():
	global PORT, OGGENCODE, ROOTS

	parser = argparse.ArgumentParser()
	parser.add_argument('folders', metavar='NAME=PATH', nargs='+', help='give access to PATH under /NAME/')
	parser.add_argument('-p', '--port', metavar='PORT', default=8000, type=int, help='listen on PORT')
	parser.add_argument('--encode', action='store_true', help='reencode non-ogg to ogg (cpu intensive on server)')
	args = parser.parse_args()

	OGGENCODE = args.encode
	PORT = args.port
	ROOTS = {}
	for fstr in args.folders:
		fdata = fstr.split('=', 1)
		if len(fdata) != 2 or not all(fdata):
			parser.error('folders must be with format NAME=PATH')
		ROOTS[decode_u8(fdata[0])] = decode_u8(fdata[1])

	run(server_class=ThreadedServer, handler_class=AudioRequestHandler)

if __name__ == '__main__':
	main()

