<!DOCTYPE html>
<html>
<head>
	<%!
		from urllib.parse import quote

		def q(u):
			return quote(u.encode('utf-8'))
	%>
	<meta charset="utf-8" />
	<meta name="viewport" content="width=device-width, initial-scale=1.0" />
	<script src="//ajax.googleapis.com/ajax/libs/jquery/2.1.1/jquery.min.js"></script>
	<script src="_/player.js"></script>
	<link href="_/style.css" rel="stylesheet" />
	<link rel="icon" type="image/png" href="_/favicon.png" />
	<title>${relpath} - WebP3</title>
</head>
<body>
<div id="oldToolbar"><audio id="player" preload="true" controls="controls"></audio></div>

<div id="toolbar"><a id="toolPrev" href="javascript:pl_prev()">&#x23EE;</a><a id="toolPP" href="javascript:playPause()">&#x23F5;</a><a id="toolNext" href="javascript:pl_next()">&#x23ED;</a><span id="song"></span><div id="time"><span id="timeText">--:--</span></div><div id="seekbar"> </div>
</div>

<h4 class="title">${relpath}</h4>

<ul id="listing">
	<li class="parent"><a href="..">Parent</a></li>
	% for item in items:
		% if item['is_dir']:
			<li class="dir"><a href="${item['basename'] | q}/">${item['basename']}</a>/</li>
		% else:
			<li class="file ${item['is_audio'] and 'audio' or ''}"><a href="${item['basename'] | q}">${item['basename']}</a></li>
		% endif
	% endfor
</ul>

<div><a href="javascript:pl_playDir()">Play directory</a></div>

<img id="albumCover" />

</body>
</html>
