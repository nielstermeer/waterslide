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

## Get a pep440 compatible version identifier
#
# @return	pep440 compatible version string
def pep440():

	if int(version.distance) == 0:
		return version.version
	else:
		return version.version + '.dev' + version.distance

## Return a human readable version as a string
def human():
	
	# if the distance is 0, we are on a real version and not a random
	# commit build, so just return the version from the tuple
	if int(version.distance) == 0:
		return version.version
	else:
		return '-'.join(version)

## Generatie a distribution/release json structure
def generate_data_file():
	data = {
		'version': '-'.join(version),
		'buildtime': time.time(),
	}
	return json.dumps(data)

## access the distribution/release data file
#
# The function uses caching, so it accesses and decodes the file only once
def read_data_file():
	dataf = os.path.join(os.path.split(__file__)[0], 'resources/data.json')
	
	if os.path.exists(dataf):
		with open(dataf, 'r') as f:
			return json.loads(f.read())
			
	return {}

## Parse a version string in the format of <version>-<distance>-<commit>.
def parse_vstring(vstr):
	if vstr == None:
		return vstr
	
	vtuple = vstr.split('-')
	
	# return only the version named tuple if git ran sucessfully
	return (vdef(*vtuple)) if len(vtuple) == 3 else None

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

# end module documetation here, so we don't include initialisation code
## @}

# setup data. Doing it this way we can ensure we always have some kind of valid data.
temp = read_data_file()

version = parse_vstring(temp.get('version')) or of_commit("HEAD") or version
buildtime = temp.get('buildtime') or time.time()

del temp
