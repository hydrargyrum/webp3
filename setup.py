#!/usr/bin/env python3
# this project is licensed under the WTFPLv2, see COPYING.txt for details

from setuptools import setup, find_packages

import glob

setup(
	name='webp3',
	version='0.2.0',

	description='Music player web app',
	long_description='''
WebP3 is a humble web-app (server) to listen to your audio files on remote.
Typically, you host WebP3 on your personal home machine (or server) where your
music files sit, and you can then listen to the music remotely at your
workplace or on a handheld device in your browser.

No, there aren't any user-data-exploiting/social features and no, it's not
hosted on some million-dollars cloud, it's hosted on your machine.
	'''.strip(),
	url='https://github.com/hydrargyrum/webp3',
	author='Hg',
	author_email='dev+pip@indigo.re',
	license='WTFPLv2',
	classifiers=[
		'Development Status :: 4 - Beta',

		'Environment :: Web Environment',

		'Framework :: Bottle',

		'Intended Audience :: End Users/Desktop',

		'License :: CC0 1.0 Universal (CC0 1.0) Public Domain Dedication',
		'License :: Public Domain',

		'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
		'Topic :: Multimedia :: Sound/Audio :: Players',

		'Programming Language :: Python :: 3',
		'Programming Language :: Python :: 3.2',
		'Programming Language :: Python :: 3.3',
		'Programming Language :: Python :: 3.4',
		'Programming Language :: Python :: 3.5',
		'Programming Language :: Python :: 3.6',
	],
	keywords='music server web player html5 audio',

	install_requires=[
		'bottle',
		'Mako > 1.0',
	],
	python_requires='>=3',

	zip_safe=False,
	packages=find_packages(),
	include_package_data=True,
	data_files=[
		('share/webp3/apache', [
			'apache/webp3.conf', 'apache/install-webp3.rst',
		]),
	],

	entry_points={
		'console_scripts': [
			'webp3=webp3:main',
		]
	}
)
