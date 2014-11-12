## What is WebP3? (use case)

WebP3 is a humble web-app (server) to play your audio files remotely. Typically, you host WebP3 on your personal home machine (or server) where your music files sit, and you can then play the music at work or on a device in your browser.

No, there aren't any user-data-exploiting/social features and no, it's not hosted on some million-dollars cloud.

## Design

WebP3 exposes a tree of folders and files that can be browsed through the web interface. A few roots are specified on the command-line to run WebP3, and all the content under those roots is exposed, there are no fine-grained permissions.

It is designed to serve trees with a folder is an album (or contains other folders). ID3 is not necessary as it's not used.

![Screenshot](screenshot.png)

### Format support

WebP3 doesn't use Flash and solely relies on HTML5's `<audio>` tag. File format support (like mp3) depends on your browser and OS.

## Usage

First, run something like:

`webp3.py -p 8000 music=/path/to/some/files music2=/another/folder/to/share`

There will be 2 roots, serving the full content of /path/to/some/files and /another/folder/to/share.
The command will not terminate, the files are served as long as it's running. Open `http://localhost:8000` to see (and play!) the music.

### Options

`-p PORT`

WebP3 will listen on port (default: 8000)

## License

WebP3 is licensed under the [do What The Fuck you want Public License v2](http://wtfpl.net).
