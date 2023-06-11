# SPDX-License-Identifier: WTFPL

from functools import wraps
import errno
import hashlib

from bottle import request, response, abort

from .exceptions import NotFound, Forbidden
from . import conf


def gen_etag(*data, path=None, weak: bool = True):
	if path:
		data = (data, path.stat())

	t = hashlib.new('md5', repr(data).encode('utf-8')).hexdigest()
	if weak:
		return 'W/"%s"' % t
	else:
		return '"%s"' % t


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


def handle_patherrors(func):
	@wraps(func)
	def decorator(*args, **kwargs):
		try:
			return func(*args, **kwargs)
		except Forbidden:
			abort(403, 'Forbidden')
		except NotFound:
			abort(404, 'Not found')

	return decorator


def base_request(func):
	return handle_patherrors(handle_oserror(func))


def handle_etag(etag):
	if not conf.MATCH_ETAG:
		return

	response.headers['ETag'] = etag
	if etag in request.headers.get('If-None-Match', ''):
		abort(304, 'Not modified')


def handle_partial(size: int):
	response.headers['Accept-Ranges'] = 'bytes'

	header = request.headers.get('Range')
	if not header:
		response.status = 200
		response.headers['Content-Length'] = size
		return slice(None)

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
	response.headers['Content-Range'] = 'bytes %s-%s/%s' % (start, end, size)
	response.headers['Content-Length'] = end - start + 1
	return slice(start, end + 1)


def slice_partial(data):
	datarange = handle_partial(len(data))
	if datarange:
		return data[datarange]


def accepted_mimes() -> list:
	# very rough parsing, to be improved if necessary
	try:
		header = request.headers['accept']
	except KeyError:
		return []
	return [t.split(';')[0] for t in header.split(',')]


def is_json_request() -> bool:
	try:
		return accepted_mimes()[0] == 'application/json'
	except IndexError:
		return False


def is_m3u_request() -> bool:
	if 'm3u' in request.query:
		return True
	try:
		return accepted_mimes()[0] == 'audio/x-mpegurl'
	except IndexError:
		return False
