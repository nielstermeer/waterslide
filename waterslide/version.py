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

# setup data. Doing it this way we can ensure we always have some kind of valid data.
temp = read_data_file()

version = parse_vstring(temp.get('version')) or of_commit("HEAD") or vdef('0.0.0', 0, '0')
buildtime = temp.get('buildtime') or time.time()

del temp
## @}
