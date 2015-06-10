/** You can redistribute this file and/or modify it under the terms of the WTFPLv2 [see /_/COPYING.WTFPL] */

var playlist = [];
var playlist_index = 0;

/* pad(7, 3) == "007" */
function pad(n, width, z) {
	z = z || '0';
	n = n + '';
	return n.length >= width ? n : new Array(width - n.length + 1).join(z) + n;
}

/* duration2str(90) == "01:30" */
function duration2str(t) {
	return pad(parseInt(t / 60), 2) + ":" + pad(parseInt(t % 60), 2);
}

function isPlaying() {
	return !$("#player").get(0).paused;
}

function pl_skip(i) {
	var playing = isPlaying();

	playlist_index += i;
	playlist_index %= playlist.length;

	load(playlist[playlist_index]);
	if (playing)
		play();
}

function pl_next() {
	pl_skip(1);
}

function pl_prev() {
	pl_skip(-1);
}

function pl_enqueueDir() {
	playlist = [];
	$(".file.audio a").each(function() {
		playlist.push(this.href);
	});
	playlist_index = 0;

	$("#player").attr("src", playlist[playlist_index]);
	$("#player").on("ended", function() {
		pl_next();
		if (playlist_index != 0)
			pl_play();
	});

	load(playlist[playlist_index]);
}

function pl_play() {
	load(playlist[playlist_index]);
	play();
}

function load(url) {
	var name = decodeURIComponent(url.replace(/\+/g, '%20'));
	name = name.substring(name.lastIndexOf('/') + 1);
	name = name.substring(0, name.lastIndexOf('.'));

	$("#song").text(name);
	$("#player").attr("src", url);
}

function play() {
	$("#player").get(0).play();
}

function pause() {
	$("#player").get(0).pause();
}

function playPause() {
	if (isPlaying())
		pause();
	else
		play();
}

/* Tweak audio file links to play instead of changing document.location */
function modFilesPlay() {
	$(".file.audio a").each(function() {
		$(this).click(function() {
			$("#player").attr("src", this.href);
			// + "?convert=ogg");
			play();
			return false;
		});
	});
}

function getPath() {
	var p = unescape(document.location.pathname);
	return p;
}

function updateTitle() {
	var title = getPath();
	document.title = title + " - WebP3";
	updateCrumbs();
}

function updateCrumbs() {
	var path = getPath();
	var crumbs = path.split('/');
	var parts = [];
	parts.push('<span class="parent"><a href="/">/</a></span>');
	for (var i = 1; i < crumbs.length - 1; i++) {
		var p = crumbs.slice(0, i + 1).join('/');
		parts.push('<span class="parent"><a href="' + p + '/">' + crumbs[i] + '</a></span>/');
	}
	$('.title').html(parts.join(''));
}

/* Tweak directory links to reload the listing instead of changing document.location.
 * This avoids reloading a new page and thus avoids stopping the player.
 * Request the new page with ajax, but just replace the listing and do tweaks (title, fix links, cover image)
 */
function modDirsAjax() {
	var modDirs = function() {
		$(".dir a, .parent a").each(function() {
			$(this).click(function() {
				loadListing(this.href, true);
				return false;
			});
		});
	};

	var loadListing = function(url, push) {
		$.get(url, function(){}, "html").done(function(data) {
			$("#listing").replaceWith($(data).filter("#listing"));
			if (push)
				history.pushState(null, null, url);
			updateTitle();
			modFilesPlay();
			modDirs();
			loadCover();
			if (!isPlaying())
				pl_enqueueDir();
		});
	};

	$(window).on("popstate", function() {
		loadListing(document.location, false);
	});

	modDirs();
}

function loadCover() {
	var $image = $('.file a').filter(function() {
		return /([Ff]older|[Aa]lbum|[Ff]ront|[Ss]mall).*(jpg|jpeg|png)/.exec(this.href);
	});
	if (!$image.length)
		$image = $('.file a[href$="jpg"]');

	if ($image.length) {
		$("#albumCover").attr("src", $image.get(0).href).show();
	} else
		$("#albumCover").hide();
}

function updateSeekbar() {
	var player = $("#player").get(0);
	if (!player.duration)
		return;

	var total = 10;
	var pos = Math.min(Math.floor(player.currentTime * total / player.duration), total - 1);
	var left = (new Array(pos + 1)).join('+');
	var right = (new Array(total - pos)).join('-');
	$("#seekbar").text('|' + left + '+' + right + '|');
}

function blinkStart($s) {
	var on = function() {
		$s.css("visibility", "visible");
		$s.blinker = window.setTimeout(off, 1000);
	};
	var off = function() {
		$s.css("visibility", "hidden");
		$s.blinker = window.setTimeout(on, 500);
	};

	on();
}

function blinkStop($s) {
	window.clearTimeout($s.blinker);
}

function progressPlay() {
	$("#timeText").text(duration2str($("#player").get(0).currentTime));
	updateSeekbar();
}

$(document).ready(function() {
	$tm = $("#timeText");

	$("#player").on("playing", function() {
		//$("#toolPP").html("&#x23F8;");
		$("#toolPP").text("||");
		//blinkStop($tm);
	});

	$("#player").on("pause", function() {
		//$("#toolPP").html("&#x23F5;");
		$("#toolPP").text(">");
		//blinkStart($tm);
	});

	$("#player").on("durationchange", updateSeekbar);
	$("#player").on("timeupdate", progressPlay);

	$("#toolPrev").text("|<<");
	$("#toolNext").text(">>|");
	$("#toolPP").text(">");

	$(window).on("keypress", function(e) {
		if (e.charCode == 112) {
			playPause();
		}
	});
});

$(document).ready(modFilesPlay);
$(document).ready(modDirsAjax);
$(document).ready(loadCover);
$(document).ready(updateTitle);
$(document).ready(pl_enqueueDir);
