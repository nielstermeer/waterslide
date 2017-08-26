import subprocess
import re
from collections import namedtuple

##
#  @defgroup version Versioning module
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
	
	v = head()

	if int(v.distance) == 0:
		return v.version
	else:
		return v.version + '.dev' + v.distance

## get a version definition tuple of the git HEAD
#
# @return	vdef named tuple
def head():
	return of_commit("HEAD")

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

	# data format: v<version>-<distance>-<commit>
	# the 'v' and the newline have been stripped already, so split on the hyphens
	vtuple = vstr.split('-')
	
	# return only the version named tuple if git ran sucessfully
	return (vdef(*vtuple)) if len(vtuple) == 3 else None

## @}
