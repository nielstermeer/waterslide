from sys import argv
import os
import re
from urllib.parse import urlparse, urlunparse
from aiohttp import web
from passlib import hash

from waterslide import presentation, multiplex, httputils

##
#  @defgroup serve HTTP server module
# 
#  @addtogroup serve
#  @{
#

## Find local Reveal repositories, return the first found or default if none
# @param paths		Iterable which contains the paths to search
# @param default	Default value to return if none could be found
# @return		Path to a Reveal repository, or the default parameter
#			if none could be found
def find_local_reveal(paths, default = None):
	for d in paths:
		if os.path.exists(os.path.join(d, 'js/reveal.js')):
			return d
	return default

## Check if any presentations given have the 'local' provider configured
# @param presses	Presentations to check
# @return		True if any of the presentations need have local
#			configured, False if none
def presentation_need_locals(presses):
	for p in presses:
		if p.basepath == p.providers.get('local'):
			return True
	return False

## redirect all requests to their specific presentations when we've got a malformed url
# @param request	Request object (currently for an aiohttp server)
# @return		Redirect response.
def redirect(request):
	return web.HTTPFound('/' + request.match_info['pres'] + '/?' + request.query_string)

## Function to send a 403 forbidden status
# @param msg	message to be send
# @return	Redirect response for an aiohttp webserver
def forbidden(msg = '403: Forbidden'):
	return web.Response(status  = 403, body = msg)

## Serve configuration object
class SConf():
	
	def __init__(
		self,
		address	= '0.0.0.0',
		port	= 9090,
		single	= False,
		local_reveal = None,
	):
		self.address	= address
		self.port	= port
		self.single	= single
		self.local_reveal = local_reveal

	helptext = '''
-p, --port <port>       Port for the webserver to listen to
                        (port 9090 is the default)
-a, --addresses <addr>  Addresses to listen to (0.0.0.0 is the default)
-s, --single            Serve a single presentation in its own directory,
                        instead of directly in the root directory
-l, --local <path>      Path to a local Reveal repository.
'''

	def parse(self, argn):
		if argv[argn] in ("-p", "--port"):
			self.port = int(args.argv[argn+1])
			ret = 2
		elif argv[argn] in ("-a", "--addresses"):
			self.address = argv[argn+1]
			ret = 2
		elif argv[argn] in ("-s", "--single"):
			self.single = True
			ret = 1
		elif argv[argn] in ("-l", "--local"):
			self.reveal_local = find_local_reveal([argv[argn+1]], False)
			ret = 1
		
		else:
			return 0
		return ret

## Wrapper to initialise and start the webapp
# @param preslist	List of presentations. Required
# @param verbosity	Verbosity we will use for the output and the
#			initialisation summary. Defaults to 1
#			Possible options are:
#			0: No output besides the webserver's and the request
#				logs
#			1: initialisation summary + list of presentations served
#			2: as with 1, but also with the presentation base url
#				and path to the source directory
#
# @param sconf		Server configuration object. Required
# @param mconf		Multiplex configuration object
# @param pconf		Presentation configuration object
def run(preslist, verbosity=1, sconf = None, mconf = None, pconf = None):

	if not sconf:
		print("No server configuration provided")
		return False

	app = web.Application()
	
	httputils.startup_defaults(app, pconf, sconf, mconf)
	
	# if there is only one presentation, serve it from the document root
	# unless it is specified that we also want single presentations to be
	# served from their own directory. Define a function to handle
	# both cases
	if len(preslist) == 1 and not sconf.single:
		def add(p):
			app.router.add_route('GET', '/{tail:.*}', preslist[0].handle)
			show(p, '/')
	else:
		# add the redirect route
		app.router.add_route('GET', '/{pres}', redirect)
		def add(p):
			app.router.add_route('GET', '/' + p.slug + '/{tail:.*}', p.handle)
			show(p, '/' + p.slug + '/')

	# define an output function to show the presentation configuration,
	# depending on the verbosity level
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
		
	web.run_app(app, host=sconf.address, port=sconf.port)

## Serve subcommand
# @param argn	Argument where "Main" stopped parsing
# @param argv	Argument vector
#
# This function handles the serve subcommands features. It parses the rest of
# the commandline, after where main stopped parsing (i.e.: the arguments meant
# for the subcommand.
def serve(argn):

	helptext = \
'''Serve subcommand: Serve a presentation over HTTP

Usage:
serve [options] [presentations]

Note that when an option conflicts with any option which came previously,
the last one takes precedence

Options:
--                      No argument processing will occur after this

--local-configured      Disable an the error message emitted when a
                        presentation needs a locally served repository but it
                        is not configured (i.e.: We've got this, don't worry)

-v, --verbose           Be verbose
-z, --silent            Be silent

-h, --help              Show this helptext
'''

	# if the local reveal.js repository has been configured. If not,
	# WaterSlide will emit an error message. Can be disabled with
	# the --local-configured option
	local_configured = False
	
	# list wherein all the possible presentations get loaded during argument
	# parsing. After parsing, they get checked and loaded into the actual
	# presentation list
	maybe_list = []
	
	mconf_hash = hash.bcrypt
	verbose = 1
	
	# presenatation configuration object
	pconf = presentation.PConf()
	sconf = SConf()
	mconf = multiplex.MConf()
	mconf.autoslave = True
	
	# continue parsing
	i = argn+1
	while i < len(argv):
	
		jmp =	pconf.parse(i) or \
			sconf.parse(i) or \
			mconf.parse(i)
		
		if jmp > 0:
			i += jmp
			continue
			
		elif argv[i] in ("-v", "--verbose"):
			verbose = 2
		elif argv[i] in ("-z", "--silent"):
			verbose = 0

		elif argv[i] in ("--local-configured",):
			local_configured = True
		
		elif argv[i] in ("-h", "--help"):
			print(helptext, "".join([pconf.helptext, sconf.helptext, mconf.helptext]))
			return
		
		# stop intrepeting arguments
		elif argv[i] == "--":
			i+=1
			while i < len(argv):
				maybe_list.append(argv[i])
				i+=1
		
		else:
			maybe_list.append(argv[i])
			
		i += 1	

	if pconf.provider:
		print("Overriding Reveal.js providers with {} version".format(pconf.provider))

	# load the settings
	pconf.load(mconf)

	preslist = presentation.loadl(
			maybe_list,
			pconf,
			ptype = presentation.HTTP_Presentation,
			assoc = None,
			)
			

	# check if there are actually any valid presentations specified, abort if none	
	if len(preslist) == 0:
		print("No (valid) presentations specified")
		return False
	
	# only serve local presentations if a presentation actually needs them
	if presentation_need_locals(preslist):
		if sconf.reveal_local and os.path.exists(os.path.join(sconf.reveal_local, 'js/reveal.js')):
			print("Serving Reveal.js locally from ", sconf.reveal_local)
		elif serve_local and not local_configured:
			print("A presentation has 'local' configured as provider, but 'local' is not available")
			print("Your experience might be degraded, unless Reveal is served by another webserver under /reveal.js/")

	try:	
		run(	preslist, 
			verbosity = verbose,
			sconf = sconf,
			mconf = mconf,
			pconf = pconf,
			)
			
	except KeyboardInterrupt:
		print("Exiting")
		sys.exit(0)
		
##  @}
