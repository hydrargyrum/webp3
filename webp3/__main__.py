#!/usr/bin/env python3
# license: You can redistribute this file and/or modify it under the terms of the WTFPLv2 [see COPYING.WTFPL]

import argparse
from pathlib import Path

import bottle

from . import conf


def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('folders', metavar='NAME=PATH', nargs='+', help='give access to PATH under /NAME/')
	parser.add_argument('-p', '--port', metavar='PORT', default=8000, type=int, help='listen on PORT')
	args = parser.parse_args()

	conf.ROOTS = {}

	for fstr in args.folders:
		fdata = fstr.split('=', 1)
		if len(fdata) != 2 or not all(fdata):
			parser.error('folders must be with format NAME=PATH')
		key = fdata[0]
		if key in conf.ROOTS:
			parser.error('roots can only be specified once: %s' % key)
		conf.ROOTS[key] = Path(fdata[1])

	bottle.run(host='', port=args.port, debug=True)


if __name__ == '__main__':
	main()
