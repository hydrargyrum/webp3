#!/usr/bin/env python3
# SPDX-License-Identifier: WTFPL

import argparse
from pathlib import Path
import os

from . import conf


def main():
	from .app import bapp

	parser = argparse.ArgumentParser()
	parser.add_argument('folders', metavar='NAME=PATH', nargs='+', help='give access to PATH under /NAME/')
	parser.add_argument('-p', '--port', metavar='PORT', default=8000, type=int, help='listen on PORT')
	parser.add_argument('-b', '--base-url', help='Absolute URLs start at BASE_URL')
	parser.add_argument('--single-root', action='store_true', help="Only show a single folder directly")
	args = parser.parse_args()

	conf.ROOTS = {}
	conf.SINGLE_ROOT = args.single_root

	if args.single_root and len(args.folders) > 1:
		parser.error('there can only be one folder with --single-root')

	for fstr in args.folders:
		fdata = fstr.split('=', 1)
		if args.single_root:
			# accept foo=/dir or just /dir, force key to "media"
			fdata = ('media', fdata[-1])
		elif len(fdata) != 2 or not all(fdata):
			parser.error('folders must be with format NAME=PATH')
		key = fdata[0]
		if key in conf.ROOTS:
			parser.error('roots can only be specified once: %s' % key)
		conf.ROOTS[key] = Path(fdata[1])

	conf.BASE_URL = args.base_url or os.environ.get("WEBP3_BASEURL")

	bapp.run(host='', port=args.port, debug=True)


if __name__ == '__main__':
	main()
