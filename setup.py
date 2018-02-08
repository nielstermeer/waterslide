#! /usr/bin/python3

# (C) 2017 Niels ter Meer
# This file is part of the WaterSlide presentation program
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from setuptools import setup, find_packages
from setuptools.command.build_py import build_py
from codecs import open
from os import path
import sys
import os
import json
import time
import subprocess
import re
from waterslide import version

class dyn_data(build_py):
	def run(self):
		# honor the --dry-run flag
		if not self.dry_run:
			target_dir = os.path.join(self.build_lib, 'waterslide/resources')

			# mkpath is a distutils helper to create directories
			self.mkpath(target_dir)

			with open(os.path.join(target_dir, 'data.json'), 'w') as f:
				f.write(version.generate_data_file())

		# distutils uses old-style classes, so no super()
		build_py.run(self)


with open('README.md', 'r') as f:
	desc = f.read()

v = version.version().pep440()

if not v:
	print("Could not obtain a valid version number")
	sys.exit(1)

setup(
	cmdclass={'build_py': dyn_data},
	
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
		'netifaces',
		'pytz',
	],
	
	entry_points={
		'console_scripts': [
			'waterslide=waterslide.waterslide:main',
		],
	},
)
