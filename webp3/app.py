# license: You can redistribute this file and/or modify it under the terms of the WTFPLv2 [see COPYING.WTFPL]

import os
import json
from urllib.parse import urljoin, quote as urlquote

from bottle import route, request, response, redirect, mako_template, static_file

from .exceptions import NotFound, Forbidden
from . import conf
from .requestutils import (
	is_json_request, is_m3u_request, base_request, gen_etag, handle_etag, handle_partial, slice_partial,
)
from .pathutils import get_mime, is_audio, resolve_path, natural_sort_ci, parent


def make_item_data(path):
	basename = os.path.basename(path)
	return dict(size=os.path.getsize(path), basename=basename, is_dir=os.path.isdir(path), is_audio=is_audio(basename))


@base_request
def ls_dir(path, urlpath):
	files = os.listdir(path)

	natural_sort_ci(files)

	etag = gen_etag(path, files, is_file=True, weak=True)
	handle_etag(etag)

	items = [make_item_data(os.path.join(path, f)) for f in files]
	items.sort(key=lambda i: not i['is_dir']) # dirs first
	files = [i['basename'] for i in items if is_audio(i['basename'])]

	if is_json_request():
		response.headers['Content-Type'] = 'application/json'
		body = json.dumps(items)
	elif is_m3u_request():
		response.headers['Content-Type'] = 'audio/x-mpegurl'
		body = ''.join(urljoin(request.url, urlquote(f)) + '\n' for f in files)
	else:
		response.headers['Content-Type'] = 'text/html'
		body = mako_template(conf.TEMPLATE, items=items, files=files, relpath=urlpath, parent=parent).encode('utf-8')

	return slice_partial(body)


@route('/')
@base_request
def ls_root():
	items = [dict(size=0, basename=k, is_dir=True, is_audio=False) for k in conf.ROOTS]
	items.sort(key=lambda x: x['basename'])

	etag = gen_etag(list(conf.ROOTS), weak=True)
	handle_etag(etag)

	if is_json_request():
		response.headers['Content-Type'] = 'application/json'
		body = json.dumps(items)
	else:
		response.headers['Content-Type'] = 'text/html'
		body = mako_template(conf.TEMPLATE, items=items, files=[], relpath='/', parent='/').encode('utf-8')

	return slice_partial(body)


@route('/favicon.png')
def _static_favicon():
	return get_static('favicon.png')


@route('/robots.txt')
def _static_robots():
	return get_static('robots.txt')


@route('/_/<name>')
@base_request
def get_static(name):
	return static_file(name, root=conf.WEBPATH)


@route('/<path:path>/_/<name>')
def get_static_sub(path, name):
	return get_static(name)


@route('/<tree>')
def ls_tree(tree):
	redirect(u'%s/' % tree)


@route('/<tree>/')
@base_request
def ls_tree_trailing(tree):
	try:
		path = conf.ROOTS[tree]
	except KeyError:
		raise NotFound()

	return ls_dir(path, u'/%s' % tree)


@base_request
def get_file(path):
	etag = gen_etag(path, is_file=True, weak=False)
	handle_etag(etag)

	mime = get_mime(path)
	if mime:
		response.headers['Content-Type'] = mime

	datarange = handle_partial(os.path.getsize(path))
	has_range = datarange.stop is not None
	pos = 0

	with open(path, 'rb') as fd:
		if has_range:
			fd.seek(datarange.start)
			pos, end = datarange.start, datarange.stop

		while (not has_range) or (pos < end):
			data = fd.read(1024)
			if not data:
				break
			if has_range:
				data = data[:end - pos]
			pos += len(data)
			yield data


@route('/<tree>/<path:path>')
@base_request
def get_any(tree, path):
	if not path:
		return ls_tree(tree)

	dest = resolve_path(tree, path)
	if os.path.isfile(dest):
		return get_file(dest)
	elif os.path.isdir(dest):
		if not path.endswith('/'):
			last = os.path.basename(path)
			redirect(u'%s/' % last)
		return ls_dir(dest, u'/%s/%s' % (tree, path))
	else:
		raise Forbidden()
