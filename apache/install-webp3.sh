#!/bin/sh -e

cd `dirname $0`/..

pip3 install .

cd apache

# copy apache-specific config file
cp -v webp3.conf /etc/apache2/sites-available

echo "Please edit /etc/apache2/sites-available to specify the path where webp3 Python package is installed"
# default value is /usr/lib/python3/dist-packages/webp3
# this could actually be something like /usr/local/lib/python3.5/dist-packages/webp3

echo "After, the config can be enabled with: a2ensite webp3"

touch /etc/webp3.conf
echo "Please edit /etc/webp3.conf to specify where are the music files"

