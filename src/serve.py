import sys
import presentation
import re
from urllib.parse import urlparse, urlunparse
from aiohttp import web

##
#  @defgroup serve HTTP server module
# 
#  @addtogroup serve
#  @{
#

## Wrapper to initialise and start the webapp
# @param preslist	List of presentations. Only required argument
# @param address	Address to listen to. Defaults to localhost
# @param port		Port to listen on. Defaults to 9090
# @param single		Whether or not to serve a single presentation in the
#			document root or in it's own directory. Defaults to
#			False
# @param verbosity	Verbosity we will use for the output and the
#			initialisation summary. Defaults to 1
#			Possible options are:
#			0: No output besides the webserver's and the request
#				logs
#			1: initialisation summary + list of presentations served
#			2: as with 1, but also with the presentation base url
#				and path to the source directory
def run(preslist, address='127.0.0.1', port=9090 , single=False, verbosity=1):

	app = web.Application()
	
	# if there is only one presentation, serve it from the document root
	# unless it is specified that we also want single presentations to be
	# served from their own directory
	if len(preslist) == 1 and not single:
		def add(p):
			app.router.add_route('GET', '/', preslist[0].handle)
			app.router.add_route('GET', '/{file}', preslist[0].handle)
			show(p, '/')
	else:
		def add(p):
			app.router.add_route('GET', '/' + p.slug, p.handle)
			app.router.add_route('GET', '/' + p.slug + '/', p.handle)
			app.router.add_route('GET', '/' + p.slug + '/{file}', p.handle)
			show(p, '/' + p.slug + '/')

	if verbosity == 1:
		def show(p, root):
			print(" - " + p.title)
	elif verbosity >= 2:
		def show(p, root):
			print(" - {}\t(url: {:<15} source:{})".format(p.title, root, p.path))
	else:
		def show(p, root):
			pass

	# print the initialisation summary line
	if verbosity > 0:
		print("serving {} presentation{}:".format(len(preslist), "s" if len(preslist) > 1 else ""))
	
	# add the presenatations to the app
	for p in preslist:
		add(p)
			
	
	web.run_app(app, host=address, port=port)

## Serve subcommand
# @param argn	Argument where "Main" stopped parsing
# @param argv	Argument vector
#
# This function handles the serve subcommands features. It parses the rest of
# the commandline, after where main stopped parsing (i.e.: the arguments meant
# for the subcommand.
def serve(argn, argv):

	preslist = list()
	helptext = \
'''Serve subcommand: Serve a presentation over HTTP

Usage:
serve [options] [presentations]

Options:
-p, --port         Port for the webserver to listen to (9090 is the default)
-a, --addresses    Addresses to listen to (localhost is the default)
-s, --single       Serve a single presentation in its own directory, instead
                   of directly in the root directory
-v, --verbose      Be verbose
-z, --silent       Be silent
-h, --help         Show this helptext'''
	
	# defaults
	port = 9090
	address = '127.0.0.1'
	verbose = 1
	single = False
	
	# continue parsing
	i = argn+1
	while i < len(argv):
		if argv[i] in ("-p", "--port"):
			port = int(argv[i+1])
		elif argv[i] in ("-a", "--addresses"):
			address = argv[i+1]
		elif argv[i] in ("-v", "--verbose"):
			verbose = 2
		elif argv[i] in ("-z", "--silent"):
			verbose = 0
		elif argv[i] in ("-s", "--single"):
			single = True
		elif argv[i] in ("-h", "--help"):
			print(helptext)
			return
		else:
			obj = presentation.HTTP_Presentation(argv[i])
			if obj.isreal:
				preslist.append(obj)
			
		i += 1

	number_of_presentations = len(preslist)


	if number_of_presentations == 0:
		print("No presentations specified")
		return False

	try:
		run(preslist, address, port, single, verbose)
	except KeyboardInterrupt:
		print("Exiting")
		sys.exit(0)
		
##  @}
