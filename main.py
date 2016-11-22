#!/usr/bin/env python3
# license: You can redistribute this file and/or modify it under the terms of the WTFPLv2 [see COPYING.WTFPL]

import argparse

import bottle

import app


def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('folders', metavar='NAME=PATH', nargs='+', help='give access to PATH under /NAME/')
	parser.add_argument('-p', '--port', metavar='PORT', default=8000, type=int, help='listen on PORT')
	parser.add_argument('--encode', action='store_true', help='support reencoding non-ogg to ogg (cpu intensive on server)')
	parser.add_argument('--zip', action='store_true', help='support zipping directories (space consuming on server)')
	args = parser.parse_args()

	app.CAN_OGGENCODE = args.encode
	app.CAN_ZIP = args.zip
	app.ROOTS = {}

	for fstr in args.folders:
		fdata = fstr.split('=', 1)
		if len(fdata) != 2 or not all(fdata):
			parser.error('folders must be with format NAME=PATH')
		key = fdata[0]
		if key in app.ROOTS:
			parser.error('roots can only be specified once: %s' % key)
		app.ROOTS[key] = fdata[1]

	bottle.run(host='', port=args.port, debug=True)


if __name__ == '__main__':
	main()
