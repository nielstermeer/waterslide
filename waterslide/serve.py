import sys
import os
import re
from urllib.parse import urlparse, urlunparse
from aiohttp import web
from passlib import hash

from waterslide import presentation, multiplex

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
		address	= '127.0.0.1',
		port	= 9090,
		single	= False,
		local_reveal = None,
	):
		self.address	= address
		self.port	= port
		self.single	= single
		self.local_reveal = local_reveal

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
	
	if mconf:
		multiplex.start_socket_io(app, mconf)
		
	
	dirname = os.path.split(__file__)[0]
	
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
	
	# check if static routing is enabled
	if pconf.static == True:
		# add a static route to resources waterslide provides
		# (currently only a better version of the multiplex plugin).
		app.router.add_static('/waterslide', os.path.join(dirname, 'web-resources'))
		
		# add a static route to a Reveal repository, if one is provided
		if sconf.local_reveal:
			app.router.add_static('/reveal.js/', sconf.local_reveal)
	
	# if the static routes have been disabled, add a diagnostic 403
	else:
		print("static is disabled")
		def no_static(request):
			return forbidden('WaterSlide static routes have been disabled')
		
		app.router.add_route('GET', '/reveal.js/{tail:.*}', no_static)
		app.router.add_route('GET', '/waterslide/{tail:.*}', no_static)
		
		
		
	web.run_app(app, host=sconf.address, port=sconf.port)

## Serve subcommand
# @param argn	Argument where "Main" stopped parsing
# @param argv	Argument vector
#
# This function handles the serve subcommands features. It parses the rest of
# the commandline, after where main stopped parsing (i.e.: the arguments meant
# for the subcommand.
def serve(argn, argv):

	helptext = \
'''Serve subcommand: Serve a presentation over HTTP

Usage:
serve [options] [presentations]

Note that when an option conflicts with any option which came previously,
the last one takes precedence

Options:
-p, --port <port>       Port for the webserver to listen to
                        (port 9090 is the default)
-a, --addresses <addr>  Addresses to listen to (0.0.0.0 is the default)

-s, --single            Serve a single presentation in its own directory,
                        instead of directly in the root directory

-l, --local <path>      Path to a local Reveal repository.
--local-configured      Disable an the error message emitted when a
                        presentation needs a locally served repository but it
                        is not configured (i.e.: We've got this, don't worry)

-o, --override <prov>   Override all configured presentation providers with
                        another provider. The availability of the new
                        provider is NOT checked.

-m, --multiplex         Enable multiplexing of presentations. This enables a
                        Socket.io server, and adds the configuration to the
                        presenations. Pass the "master" query in the url to
                        obtain control of the presenation
                        (e.g.: localhost/?master)

--no-cache              Do not send caching headers

--disable-static        Disable static file routes, for when another webserver
                        is handling them for us

-v, --verbose           Be verbose
-z, --silent            Be silent

-h, --help              Show this helptext

--                      No argument processing after this'''
	
	sconf = SConf()
	
	ovr_provider = False	# Override argument
	# if the local reveal.js repository has been configured. If not,
	# WaterSlide will emit an error message. Can be disabled with
	# the --local-configured option
	local_configured = False
	
	# list wherein all the possible presentations get loaded during argument
	# parsing. After parsing, they get checked and loaded into the actual
	# presentation list
	maybe_list = []
	
	do_multiplex = False
	mconf_hash = hash.bcrypt
	verbose = 1
	
	# presenatation configuration object
	pconf = presentation.PConf()
	
	# continue parsing
	i = argn+1
	while i < len(argv):
		if argv[i] in ("-p", "--port"):
			sconf.port = int(argv[i+1])
			i += 1
		elif argv[i] in ("-a", "--addresses"):
			sconf.address = argv[i+1]
			i += 1 # skip the next argument
			
		elif argv[i] in ("-v", "--verbose"):
			verbose = 2
		elif argv[i] in ("-z", "--silent"):
			verbose = 0
			
		elif argv[i] in ("-s", "--single"):
			sconf.single = True
			
		elif argv[i] in ("-l", "--local"):
			sconf.reveal_local = find_local_reveal([argv[i+1]], False)
			i += 1
		elif argv[i] in ("--local-configured",):
			local_configured = True
		
		elif argv[i] in ("-o", "--override"):
			temp = argv[i+1]
			
			if temp in presentation.Presentation.providers.keys():
				pconf.provider = temp
				i+=1
		
		elif argv[i] in ("-m", "--multiplex"):
			do_multiplex = True
		
		elif argv[i] in ("--no-cache",):
			pconf.cache = False
		
		elif argv[i] in ("--disable-static",):
			pconf.static = False
		
		elif argv[i] in ("-h", "--help"):
			print(helptext)
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

	if ovr_provider:
		print("Overriding Reveal.js providers with {} version".format(ovr_provider))


	# load the settings
	mconf = multiplex.MConf(htype = mconf_hash, rlen=multiplex.MConf.deflen) if do_multiplex else None

	pconf.mconf = mconf

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
