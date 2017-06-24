# license: You can redistribute this file and/or modify it under the terms of the WTFPLv2 [see COPYING.WTFPL]

from __future__ import print_function
import sys
import os

import bottle
import webp3.conf
import webp3.app


def read_conf(environ):
	path = environ.get('webp3.conf', '/etc/webp3.conf')
	if not os.path.exists(path):
		raise RuntimeError('missing config file')

	with open(path) as conf:
		roots = {}
		for line in conf:
			line = line.rstrip()

			try:
				key, dest = line.split('=', 1)
			except ValueError:
				raise RuntimeError('lines must be in format NAME=PATH')

			if key in roots:
				raise RuntimeError('duplicate key %r' % key)

			roots[key] = dest
		webp3.conf.ROOTS = roots


def decorate(func):
	def wrapper(environ, starter):
		read_conf(environ)
		return func(environ, starter)

	return wrapper


application = bottle.default_app()
application.wsgi = decorate(application.wsgi)
