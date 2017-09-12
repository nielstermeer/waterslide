# (C) 2017 Niels ter Meer
# This file is part of the WaterSlide presentation program
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from sys import argv
import os
from waterslide import serve, presentation, version, manager
import datetime, time

##
#  @defgroup main Main module
# 
#  @addtogroup main
#  @{
#

## default function, triggered in "main" when no subcommand was specified
# @param argn	Argument number of where main stopped parsing them. Isn't used
# @param argv	Argument vector. Isn't used
def no_func(argn):
	print("No subcommand provided")

## Function to show the waterslide program version
# @copydetails no_func
def show_version(argn):
	
	helptext = \
"""Version information options:

<none>             show a normal version and warranty text
--help             show this helptext
--describe         print the 'git describe' output for this version
--release          print the release tag
--btime            print buildtime
--commit           print commit id
--pep440           print pep440 compatible version string

All these options are mutually exclusive. If more than one is given, then
the highest option in the above list takes precedence.

example (for in source directory):
git checkout `waterslide version --commit` # checkout commit this was build from
git checkout `waterslide version --release`# checkout base release"""
	
	args = argv[argn:]
	v = version.version
	
	t = version.buildtime
	tf =  datetime.datetime.fromtimestamp(
			int(t)
		).strftime('%Y-%m-%d %H:%M:%S')
	
	if "--help" in args:
		print(helptext)	
	elif "--describe" in args:
		print("v" + '-'.join(v))
	elif "--btime" in args:
		print(tf)
	elif "--release" in args:
		print("v" + version.human())
	elif "--commit" in args:
		print(v.commit)
	elif "--pep440" in args:
		print(version.pep440())
	else:
		print("waterslide v{} ({})".format(version.human(), tf))
		print("Copyright (C) Niels ter Meer")


## show configuration related data
# @copydetails no_func
def conf(argn):

	helptext = \
'''Configuration information dump subcommand

sources:
wwwdata-path       Get the path to the web related data. Can be used to
                   configure a webserver
                   Options:
                   --nginx   Get an NginX configuration block which
                             will serve the web data
                   <none>    Just serve the data

data-path         Get the path to the program's internal data. Currently only
                  contains the versioning information file
'''

	arg = argv[argn+1]
	args = argv[argn+2:]

	if arg == "wwwdata-path":
		
		path = os.path.join(os.path.split(__file__)[0], 'web-resources')
		
		if "--nginx" in args:
			print("\n".join([
				"location /waterslide {",
				"\troot {};".format(path),
				"\ttry_files $uri =404;",
				"}"
				])
			)
		else:
			print(path)
		
	elif arg == "data-path":
		path = print(os.path.join(os.path.split(__file__)[0], 'resources'))

	else:
		print("No configuration data recognised")


# stop the main module here, as to not include the variables used within the
# "main" function below here
## @}

# "Main" function below here
# ----
def main():
	helptext = '''
Waterslide: Presentation build program, build around Reveal.js
Usage: waterslide [options] [subcommand [options]]

Main options:
--version          Show version and exit (see also version --help)
-h, --help         Show this helptext and exit

Subcommands:
serve              Serve (a) presentation(s) over http
conf               Show configuration related data, paths and such
version            see --version
'''

	# commandline defaults
	subcmd = no_func

	# start parsing arguments
	i = 1
	while i < len(argv):
		if argv[i] in ("--version", "version"):
			subcmd = show_version
			break
		elif argv[i] in ("-h", "--help"):
			print(helptext)
			sys.exit(0)
		elif argv[i] == "serve":
			subcmd = serve.serve
			break
		elif argv[i] == "conf":
			subcmd = conf
			break
		elif argv[i] == "manage":
			subcmd = manager.serve
			break
	
		i += 1

	# Trigger the subcommand
	return subcmd(i)
