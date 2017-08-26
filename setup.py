#! /usr/bin/python3
from setuptools import setup, find_packages
from codecs import open
from os import path
import subprocess
import re

def coerce_version():
	# the version is the output of the git describe command, up to but not including the trailing newline
	vstr = (subprocess.Popen(["git", "describe", "--first-parent"], stdout=subprocess.PIPE)).communicate()[0].decode("utf8")[:-1]
	
	t = re.split('-', vstr)
	
	# strip the namespacing 'v' of the front
	version = t[0][1:]
	dev_v = '-dev' + t[1] if len(t) == 2 else ''
	
	return version + dev_v

with open('README.md', 'r') as f:
	desc = f.read()

print(find_packages())

setup(
	name = 'waterslide',
	
	version = coerce_version(),
	
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
