# license: You can redistribute this file and/or modify it under the terms of the WTFPLv2 [see COPYING.WTFPL]

from __future__ import print_function
import sys
import os

import bottle

os.chdir(os.path.dirname(__file__))
sys.path.append(os.path.abspath('.'))

import app


with open('share.conf') as conf:
	for line in conf:
		line = line.rstrip()

		try:
			key, dest = line.split('=', 1)
		except ValueError:
			print('lines must be in format NAME=PATH', file=sys.stderr)
			sys.exit(1)

		if key in app.ROOTS:
			print('duplicate key %r' % key, file=sys.stderr)
			sys.exit(1)

		app.ROOTS[key] = dest

application = bottle.default_app()
