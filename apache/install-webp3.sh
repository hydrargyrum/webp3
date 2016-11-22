#!/bin/sh -e

# copy apache-specific config file
cp webp3.conf /etc/apache2/sites-available
# the config can be enabled with: a2ensite webp3

TARGET=/srv/www/webp3
# path where the webp3 app files (not music files!) will be installed
# if this path is edited, webp3.conf MUST be edited as well

mkdir -p $TARGET
cp -R ../app.py ../app.wsgi ../static $TARGET

[ -f $TARGET/share.conf ] || touch $TARGET/share.conf
# edit share.conf to specify where are the music folders
