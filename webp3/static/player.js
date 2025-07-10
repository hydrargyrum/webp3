/** SPDX-License-Identifier: WTFPL */

var useRemainingTime = false;
var playlist = [];
var playlist_index = 0;

/* duration2str(90) == "01:30" */
function duration2str(t) {
	var pt = Math.abs(t);
	var s = `${parseInt(pt / 60)}`.padStart(2, "0") + ":" + `${parseInt(pt % 60)}`.padStart(2, "0");

	if (t < 0)
		return `-${s}`;
	return s;
}

function unquote(url) {
	return decodeURIComponent(url.replace(/\+/g, '%20'));
}

function isPlaying() {
	return !document.querySelector("#player").paused;
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
	for (let link of document.querySelectorAll(".file.audio a")) {
		playlist.push(link.href);
	}
	playlist_index = 0;

	if (playlist.length) {
		document.querySelector("#player").src = playlist[playlist_index];
		load(playlist[playlist_index]);
	}
}

function pl_play() {
	load(playlist[playlist_index]);
	play();
}

function load(url) {
	var name = unquote(url);
	name = name.substring(name.lastIndexOf('/') + 1);
	name = name.substring(0, name.lastIndexOf('.'));

	document.querySelector("#song").innerText = name;
	document.querySelector("#player").src = url;
}

function play() {
	document.querySelector("#player").play();
}

function pause() {
	document.querySelector("#player").pause();
}

function playPause() {
	if (isPlaying())
		pause();
	else
		play();
}

/* Tweak audio file links to play instead of changing document.location */
function modFilesPlay() {
	for (let link of document.querySelectorAll(".file.audio a")) {
		link.addEventListener("click", function(event) {
			document.querySelector("#player").src = event.target.href;
			// + "?convert=ogg");
			play();
			event.preventDefault();
			return false;
		});
	}
}

function getPath() {
	var p = unquote(document.location.pathname);
	return p;
}

function updateTitle() {
	var title = getPath();
	document.title = `${title} - WebP3`;
	updateCrumbs();
}

function updateCrumbs() {
	var path = getPath();
	var crumbs = path.split('/');
	var parts = [];
	parts.push('<span class="parent"><a href="/">/</a></span>');
	for (var i = 1; i < crumbs.length - 1; i++) {
		var p = crumbs.slice(0, i + 1).join('/');
		parts.push(`<span class="parent"><a href="${p}/">${crumbs[i]}</a></span>/`);
	}
	document.querySelector('.title').innerHTML = parts.join('');
}

/* Tweak directory links to reload the listing instead of changing document.location.
 * This avoids reloading a new page and thus avoids stopping the player.
 * Request the new page with ajax, but just replace the listing and do tweaks (title, fix links, cover image)
 */
function modDirsAjax() {
	var modDirs = function() {
		for (let link of document.querySelectorAll(".dir a, .parent a")) {
			link.addEventListener("click", function(event) {
				loadListing(this.href, true);
				event.preventDefault();
				return false;
			});
		}
	};

	var loadListing = function(url, push) {
		fetch(url).then(function(response) {
			if (!response.ok) {
				return;
			}
			return response.text();
		}).then(function(text) {
			if (!text) {
				return;
			}
			var parser = new DOMParser();
			var newdoc = parser.parseFromString(text, "text/html");
			var newlisting = newdoc.getElementById("listing").cloneNode(true);
			var listing = document.querySelector("#listing");
			listing.parentNode.replaceChild(newlisting, listing);
			if (push) {
				history.pushState(null, null, url);
			}
			updateTitle();
			modFilesPlay();
			modDirs();
			loadCover();
			if (!isPlaying()) {
				pl_enqueueDir();
			}
		});
	};

	window.addEventListener("popstate", function() {
		loadListing(document.location, false);
	});

	modDirs();
}

function loadCover() {
	var images = Array.from(document.querySelectorAll('.file a')).filter(function(link) {
		return /([Ff]older|[Aa]lbum|[Ff]ront|[Ss]mall).*(jpg|jpeg|png)/.exec(link.href);
	});
	if (!images.length) {
		images = Array.from(document.querySelectorAll('.file a[href$="jpg"]'));
	}

	if (images.length) {
		document.querySelector("#albumCover").src = images[0].href;
		document.querySelector("#albumCover").style.display = "inline";
	} else {
		document.querySelector("#albumCover").style.display = "none";
	}
}

function updateSeekbar() {
	var player = document.querySelector("#player");
	if (!player.duration)
		return;

	var total = 10;
	var pos = Math.min(Math.floor(player.currentTime * total / player.duration), total - 1);
	document.querySelector("#seekbar").innerText = "|" + "+".repeat(pos + 1) + "-".repeat(total - pos - 1) + "|";
}

function doSeek(event) {
	var seeking = event.target.data_seeking;

	if (!seeking)
		return;

	var player = document.querySelector("#player");
	var ratio = event.offsetX / event.target.offsetWidth;
	var newTime = ratio * player.duration;

	player.currentTime = newTime;
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
	var pos = document.querySelector("#player").currentTime;
	if (useRemainingTime)
		pos -= document.querySelector("#player").duration;

	document.querySelector("#timeText").innerText = duration2str(pos);
	updateSeekbar();
}

window.addEventListener("load", function() {
	let $tm = document.querySelector("#timeText");

	document.querySelector("#player").addEventListener("playing", function() {
		document.querySelector("#toolPP").innerText = "||";
		//blinkStop($tm);
	});

	document.querySelector("#player").addEventListener("pause", function() {
		document.querySelector("#toolPP").innerText = ">";
		//blinkStart($tm);
	});

	document.querySelector("#player").addEventListener("durationchange", updateSeekbar);
	document.querySelector("#player").addEventListener("timeupdate", progressPlay);
	document.querySelector("#player").addEventListener("ended", function() {
		pl_next();
		if (playlist_index != 0)
			pl_play();
	});

	document.querySelector("#seekbar").addEventListener("mousedown", function(ev) {
		ev.target.data_seeking = true;
		doSeek(ev);
	});
	document.querySelector("#seekbar").addEventListener("mousemove", doSeek);
	document.querySelector("#seekbar").addEventListener("mouseout", function(ev) {
		ev.target.data_seeking = false;
	});
	document.querySelector("#seekbar").addEventListener("mouseup", function(ev) {
		ev.target.data_seeking = false;
	});

	window.addEventListener("keypress", function(e) {
		switch (e.key) {
		case "p":
			playPause();
			break;
		case "<":
			pl_prev();
			break;
		case ">":
			pl_next();
			break;
		}
	});
});

window.addEventListener("load", modFilesPlay);
window.addEventListener("load", modDirsAjax);
window.addEventListener("load", loadCover);
window.addEventListener("load", updateTitle);
window.addEventListener("load", pl_enqueueDir);
