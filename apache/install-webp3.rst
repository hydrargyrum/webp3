To install WebP3 as a WSGI app under Apache:

* copy apache/webp3.conf to /etc/apache2/sites-available
* edit /etc/webp3.conf to add NAME=PATH entries, one-per-line, see README
* run "a2ensite webp3" to enable WebP3 in Apache
* run "service apache2 reload" to make Apache reload its configuration and start WebP3
