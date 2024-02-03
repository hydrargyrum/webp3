# SPDX-License-Identifier: WTFPL

import os
from pathlib import Path

import webp3.conf
import webp3.app


def read_conf(environ):
	single_root = os.environ.get("WEBP3_SINGLE_ROOT")
	if single_root:
		if not os.path.exists(single_root):
			raise FileNotFoundError(f"media root {single_root!r} does not exist")
		webp3.conf.SINGLE_ROOT = True
		webp3.conf.ROOTS = {"media": Path(single_root)}
	else:
		conf_path = environ.get('webp3.conf', os.environ.get('WEBP3_CONF', '/etc/webp3.conf'))
		read_conf_file(conf_path)

	webp3.conf.BASE_URL = os.environ.get("WEBP3_BASEURL")


def read_conf_file(path):
	if not os.path.exists(path):
		raise FileNotFoundError(f'missing config file {path}')

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

			roots[key] = Path(dest)
		webp3.conf.ROOTS = roots


def decorate(func):
	def wrapper(environ, starter):
		read_conf(environ)
		return func(environ, starter)

	return wrapper


application = webp3.app.bapp
application.wsgi = decorate(application.wsgi)
