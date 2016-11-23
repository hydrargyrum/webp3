# license: You can redistribute this file and/or modify it under the terms of the WTFPLv2 [see COPYING.WTFPL]

import os


ROOTS = {}

MATCH_ETAG = True

AUDIO_EXTENSIONS = {
	'.flac': 'audio/flac',
	'.ogg': 'audio/ogg',
	'.mp3': 'audio/mpeg',
	'.wav': 'audio/x-wav',
	'.m4a': 'audio/mpeg'
}

WEBPATH = os.path.join(os.path.dirname(__file__), 'static')

TEMPLATE = os.path.join(WEBPATH, 'base.tpl')
