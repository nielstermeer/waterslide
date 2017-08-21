#! /usr/bin/python3

import sys
import serve
import presentation

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
	print("Very WIP")

# stop the main module here, as to not include the variables used within the
# "main" function below here
## @}

# "Main" function below here
# ----

helptext = \
'''Waterslide: Presentation build program, build around Reveal.js

Usage: waterslide [options] [subcommand [options]]

Main options:
--version          Show version and exit
-h, --help         Show this helptext and exit

Subcommands:
serve              Serve (a) presentation(s) over http'''

# commandline defaults
subcmd = no_func

# start parsing arguments
i = 1
while i < len(sys.argv):
	if sys.argv[i] == "--version":
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
subcmd(i, sys.argv)
