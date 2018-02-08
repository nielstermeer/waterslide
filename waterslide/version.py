# (C) 2017 Niels ter Meer
# This file is part of the WaterSlide presentation program
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import subprocess
import re
from collections import namedtuple
import json
import os
import time
import datetime

##
#  @defgroup version Versioning module
#
# This module takes care of figuring out the program's version information
#
#  @addtogroup version
#  @{
#

## version definition tuple, based upon "git describe"'s output
vdef = namedtuple('vdef', ['version', 'distance', 'commit'])

## Parse a version string in the format of <version>-<distance>-<commit>.
def parse_vstring(vstr):
	if vstr == None:
		return vstr
	
	vtuple = vstr.split('-')
	
	# return only the version named tuple if git ran sucessfully
	return (vdef(*vtuple)) if len(vtuple) == 3 else None

## Generatie a distribution/release json structure
def generate_data_file(skip_data_file = False):
	data = {
		'version': version(skip_data_file).human(),
		'buildtime': time.time(),
	}
	return json.dumps(data)

## access the distribution/release data file
#
# The function uses caching, so it accesses and decodes the file only once
def read_data_file(fname = None):
	dataf = fname or os.path.join(os.path.split(__file__)[0], 'resources/data.json')
	
	if os.path.exists(dataf):
		with open(dataf, 'r') as f:
			return json.loads(f.read())
			
	return {}

## get the version definition tuple of a commit
#
# @param commit_ish	A git commit identifier. See the git-describe manpage
# @return		vdef tuple containing the version, or none on failure
def of_commit(commit_ish = "HEAD"):
	# the version is the output of the git describe command, from 
	# the 'v' up to but not including the trailing newline.
	vstr = (subprocess.run(["git", "describe", "--long", "--first-parent", "--match=v*", commit_ish],
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE
			)
		) \
		.stdout \
		.decode("utf8")[1:-1] #strip the 'v' and '\n' at the beginning and the end
	
	return parse_vstring(vstr)

class version:
	
	## Program version information.
	#
	# Defaults to zeroes, get's updated during module initalisation. It first
	# checks the datafile (which shouldn't exists while developing), and then
	# resorts to asking git for the data.
	version		= vdef('0.0.0', 0, '0')
	
	## program buildtime.
	#
	# Defaults to 0, but gets updated during module initialisation. It first
	# checks the datafile (which shouldn't exists while developing), and then
	# resorts to asking git for the data.
	buildtime	= 0
	
	## Initialise version object
	def __init__(self, skip_data_file = False):

		# only attempt to read data files if we're allowed to do so	
		t = {} if skip_data_file else \
			read_data_file('data.json') or read_data_file()
		
		self.version = parse_vstring(t.get('version')) or of_commit() or version
		self.buildtime = t.get('buildtime') or time.time()
		

	## Get a pep440 compatible version identifier
	#
	# @return	pep440 compatible version string
	def pep440(self):

		if int(self.version.distance) == 0:
			return self.version.version
		else:
			return self.version.version + '.dev' + self.version.distance

	## Return a human readable version as a string
	def human(self):
		
		# if the distance is 0, we are on a real version and not a random
		# commit build, so just return the version from the tuple
		if int(self.version.distance) == 0:
			return self.version.version
		else:
			return '-'.join(self.version)
	
	def describe(self):
		return '-'.join(self.version)
	
	def commit(self):
		return self.version.commit
	
	def btime(self, fmt = '%Y-%m-%d %H:%M:%S'):
		return datetime.datetime.fromtimestamp(int(self.buildtime)).strftime(fmt)

# end module
## @}
