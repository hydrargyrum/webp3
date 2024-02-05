# SPDX-License-Identifier: WTFPL

from collections import namedtuple
import os
import re
import hashlib
import mimetypes
from pathlib import Path
from typing import List

from .exceptions import Forbidden, NotFound
from . import conf


Request = namedtuple('Request', ('tree', 'root', 'path', 'target'))


def natural_sort_ci(paths: List[Path]) -> List[Path]:
	def try_int(v: str):
		try:
			# force ints < strs
			return (0, int(v))
		except ValueError:
			return (1, v)

	def natural_sort_ci_key(k):
		return [try_int(v) for v in re.findall(r'\d+|\D+', k.name.lower())]

	paths.sort(key=natural_sort_ci_key)


def gen_etag(*data, path=None, weak: bool = True) -> str:
	if path:
		data = (data, path.stat())
	t = hashlib.new('md5', repr(data).encode('utf-8')).hexdigest()
	if weak:
		return 'W/"%s"' % t
	else:
		return '"%s"' % t


def is_audio(path: Path) -> bool:
	return any(path.name.endswith(ext) for ext in conf.AUDIO_EXTENSIONS)


def get_mime(path: Path) -> str:
	for ext in conf.AUDIO_EXTENSIONS:
		if path.name.endswith(ext):
			return conf.AUDIO_EXTENSIONS[ext]
	return mimetypes.guess_type(str(path))[0]


def build_request_path(tree: str, reqpath: str) -> Request:
	try:
		root = conf.ROOTS[tree]
	except KeyError:
		raise NotFound()

	# path.resolve() would resolve symlinks, which might be an info leak...
	# sad pathlib is incapable of normalizing (removing ".." etc.) a path
	# without following symlinks
	path = Path(os.path.normpath(reqpath))

	assert path.is_absolute()
	path = Path(*path.parts[1:])
	assert not path.is_absolute()

	target = root.joinpath(path).resolve()
	assert target.relative_to(root)

	return Request(tree=tree, root=root, path=path, target=target)


def check_build_request_path(tree: str, reqpath: str) -> Request:
	req = build_request_path(tree, reqpath)

	if req.target.is_symlink():
		raise Forbidden()
	if not req.target.exists():
		raise NotFound()
	return req


def relative_to_root(current: Path) -> Path:
	times = len(current.parts)
	if not conf.SINGLE_ROOT:
		times += 1
	return Path(*(".." for _ in range(times)))
