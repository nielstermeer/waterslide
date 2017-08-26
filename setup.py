#! /usr/bin/python3
from setuptools import setup, find_packages
from codecs import open
from os import path
import sys
import subprocess
import re
from waterslide import version

with open('README.md', 'r') as f:
	desc = f.read()

v = version.pep440()

if not v:
	print("Could not obtain a valid version number")
	sys.exit(1)

setup(
	name = 'waterslide',
	
	version = v,
	
	description = "Plug and Play Reveal.js presenations",
	
	long_description = desc,
	
	author = "Niels ter Meer",
	author_email = "nielstermeer.business@gmail.com",
	
	python_requires='>=3, <4',
	
	# adding packages
	packages = ['waterslide'],
	package_data={'waterslide': ['web-resources/*']},
	
	install_requires = [
		'aiohttp',
		'libsass',
		'python-socketio',
		'PyYAML',
		'passlib',
		'bcrypt',
		'netifaces',
		'pytz',
	],
	
	entry_points={
		'console_scripts': [
			'waterslide=waterslide.waterslide:main',
		],
	},
)
