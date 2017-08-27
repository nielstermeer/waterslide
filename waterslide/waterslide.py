import sys
import os
from waterslide import serve, presentation, version
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
def no_func(argn, argv):
	print("No subcommand provided")

## Function to show the waterslide program version
# @copydetails no_func
def show_version(argn, argv):
	
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

# stop the main module here, as to not include the variables used within the
# "main" function below here
## @}

# "Main" function below here
# ----
def main():
	helptext = \
'''Waterslide: Presentation build program, build around Reveal.js
Usage: waterslide [options] [subcommand [options]]

Main options:
--version          Show version and exit (see also version --help)
-h, --help         Show this helptext and exit

Subcommands:
serve              Serve (a) presentation(s) over http
version            see --version'''

	# commandline defaults
	subcmd = no_func

	# start parsing arguments
	i = 1
	while i < len(sys.argv):
		if sys.argv[i] in ("--version", "version"):
			subcmd = show_version
			break
		elif sys.argv[i] in ("-h", "--help"):
			print(helptext)
			sys.exit(0)
		elif sys.argv[i] == "serve":
			subcmd = serve.serve
			break
	
		i += 1

	# Trigger the subcommand
	return subcmd(i, sys.argv)
