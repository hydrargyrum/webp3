# license: You can redistribute this file and/or modify it under the terms of the WTFPLv2 [see COPYING.WTFPL]

import os
import re
import hashlib
import mimetypes

from .exceptions import Forbidden, NotFound
from . import conf


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
	return any(name.endswith(ext) for ext in conf.AUDIO_EXTENSIONS)


def get_mime(path):
	for ext in conf.AUDIO_EXTENSIONS:
		if path.endswith(ext):
			return conf.AUDIO_EXTENSIONS[ext]
	return mimetypes.guess_type(path)[0]


def parent(s):
	"""
	>>> parent('/foo/bar')
	'/foo'
	>>> parent('/foo/bar/')
	'/foo'
	"""

	if s.endswith('/'):
		s = s[:-1]
	return os.path.dirname(s)


def norm(path):
	"""
	>>> norm('foo//bar/../bar/')
	'foo/bar'
	>>> norm('foo/../..')
	Traceback (most recent call last):
	Forbidden
	>>> norm('/foo')
	Traceback (most recent call last):
	Forbidden
	"""

	path = os.path.normpath(path)
	if os.path.isabs(path):
		raise Forbidden()
	elif path == '..' or path.startswith('..' + os.sep):
		raise Forbidden()
	return path


def resolve_path(tree, path):
	if tree not in conf.ROOTS:
		raise NotFound()

	path = norm(path)

	root = conf.ROOTS[tree]
	res = os.path.join(root, path)

	if not os.path.exists(res):
		raise NotFound()

	return res
