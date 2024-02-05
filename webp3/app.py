# SPDX-License-Identifier: WTFPL

import json
from urllib.parse import urljoin, quote as urlquote
from pathlib import Path

from bottle import request, response, redirect, mako_template, static_file, Bottle

from .exceptions import Forbidden
from . import conf
from .requestutils import (
	is_json_request, is_m3u_request, base_request, gen_etag, handle_etag, slice_partial,
)
from .pathutils import (
	get_mime, is_audio, natural_sort_ci,
	check_build_request_path, Request, relative_to_root,
)


def make_item_data(path: Path) -> dict:
	return {
		'size': path.stat().st_size,
		'basename': path.name,
		'is_dir': path.is_dir(),
		'is_audio': is_audio(path),
		'path': path,
	}


bapp = Bottle()


def build_absolute_url(req, name: str) -> str:
	path = str(req.path)
	if conf.BASE_URL:
		urlparts = [conf.BASE_URL.rstrip("/"), req.tree, path, urlquote(name)]
		if conf.SINGLE_ROOT:
			del urlparts[1]
		return "/".join(urlparts)
	else:
		return urljoin(request.url, urlquote(name))


@base_request
def ls_dir(req: Request):
	files = list(req.target.iterdir())

	natural_sort_ci(files)

	etag = gen_etag(files, path=req.target, weak=True)
	handle_etag(etag)

	files = [f for f in files if not f.is_symlink() and (f.is_file() or f.is_dir())]

	def naming_sort_key(f):
		# dirs first
		return (not f.is_dir(), f.name.lower())

	files.sort(key=naming_sort_key)
	items = [make_item_data(f) for f in files]
	files = [i['basename'] for i in items if is_audio(i['path'])]

	if is_json_request():
		response.headers['Content-Type'] = 'application/json'
		body = json.dumps(items)
	elif is_m3u_request():
		response.headers['Content-Type'] = 'audio/x-mpegurl'
		body = ''.join(build_absolute_url(req, f) + '\n' for f in files)
	else:
		response.headers['Content-Type'] = 'text/html'
		body = mako_template(
			conf.TEMPLATE,
			items=items,
			files=files,
			relpath=Path('/').joinpath(req.path),
			toroot=relative_to_root(req.path),
		).encode('utf-8')

	return slice_partial(body)


@bapp.route('/')
@base_request
def ls_root():
	if conf.SINGLE_ROOT:
		return ls_tree_trailing(None)

	items = [{
		'size': 0,
		'basename': k,
		'is_dir': True,
		'is_audio': False,
		'path': conf.ROOTS[k],
	} for k in conf.ROOTS]
	items.sort(key=lambda x: x['basename'].lower())

	etag = gen_etag(list(conf.ROOTS), weak=True)
	handle_etag(etag)

	if is_json_request():
		response.headers['Content-Type'] = 'application/json'
		body = json.dumps(items)
	else:
		response.headers['Content-Type'] = 'text/html'
		body = mako_template(
			conf.TEMPLATE,
			items=items,
			files=[],
			relpath=Path('/'),
			toroot=Path('.'),
		).encode('utf-8')

	return slice_partial(body)


@bapp.route('/favicon.png')
def _static_favicon():
	return get_static('favicon.png')


@bapp.route('/robots.txt')
def _static_robots():
	return get_static('robots.txt')


@bapp.route('/_/<name>')
@base_request
def get_static(name):
	return static_file(name, root=conf.WEBPATH)


@bapp.route('/<tree>')
def ls_tree(tree):
	if conf.SINGLE_ROOT:
		return get_any(None, tree)

	redirect(f'{tree}/')


@bapp.route('/<tree>/')
@base_request
def ls_tree_trailing(tree):
	if conf.SINGLE_ROOT:
		if tree is None:
			tree = "media"
		else:
			return get_any(None, f"{tree}/")

	req = check_build_request_path(tree, '/')
	return ls_dir(req)


@base_request
def get_file(path: Path):
	etag = gen_etag(path=path, weak=False)
	handle_etag(etag)

	mime = get_mime(path)
	if mime:
		response.headers['Content-Type'] = mime

	return static_file(path.name, str(path.parent))


@bapp.route('/<tree>/<path:path>')
@base_request
def get_any(tree, path):
	if conf.SINGLE_ROOT:
		if tree is None:
			tree = "media"
		else:
			path = f"{tree}/{path}"
			tree = "media"

	if not path:
		return ls_tree(tree)

	req = check_build_request_path(tree, f'/{path}')
	dest = req.target

	if dest.is_file():
		return get_file(dest)
	elif dest.is_dir():
		if not path.endswith('/'):
			redirect(f'{path.name}/')
		return ls_dir(req)
	else:
		raise Forbidden()
