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

## Possible locations of a Reveal.js repositories
#
# These can be used to point a static route at them, so that resources can be
# requested from the same host, instead of from the internet, which the
# other providers do
hints = (
	os.path.join(os.path.expanduser("~"), 'reveal.js'),
	'/usr/local/share/reveal.js'
)

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

# redirect all requests to their specific presentations when we've got a malformed url
def redirect(request):
	return web.HTTPFound('/' + request.match_info['pres'] + '/?' + request.query_string)

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
# @param local_reveal	A path to a local Reveal repository (to add a static
# 			route to, so we can serve the Reveal resources locally)
#			or None, when we don't want to add a static route
# @param mconf		Multiplex configuration
def run(preslist, address='127.0.0.1', port=9090 , single=False, verbosity=1,
	local_reveal=None, mconf = None):

	app = web.Application()
	
	if mconf:
		multiplex.start_socket_io(app, mconf)
		
	
	dirname = os.path.split(__file__)[0]
	
	# if there is only one presentation, serve it from the document root
	# unless it is specified that we also want single presentations to be
	# served from their own directory. Define a function to handle
	# both cases
	if len(preslist) == 1 and not single:
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
	
	# add a static route to a Reveal repository, if one is provided
	if local_reveal:
		app.router.add_static('/reveal.js/', local_reveal)
	
	# add a static route to resources waterslide provides (currently only a better version
	# of the multiplex plugin.
	app.router.add_static('/waterslide', os.path.join(dirname, 'web-resources'))
	
		
	web.run_app(app, host=address, port=port)

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
-L, --find-local        Attempt to find a local Reveal repository from a list
                        of builtin possible locations.
-d, --dont-local        Don't search for a local version of Reveal
                        in /usr/share/reveal.js.
-n, --no-local-route    Don't add a static route for a local Reveal repository,
                        even if some presentations require it. 
                        It also supresses an error message regarding a
                        possible non-availability of a local Reveal repository.
                        This might be useful for when the local Provider is
                        served by another webserver

-o, --override <prov>   Override all configured presentation providers with
                        another provider. The availability of the new
                        provider is NOT checked.

-m, --multiplex         Enable multiplexing of presentations. This enables a
                        Socket.io server, and adds the configuration to the
                        presenations. Pass the "master" query in the url to
                        obtain control of the presenation
                        (e.g.: localhost/?master)

--no-cache              Do not send caching headers

-v, --verbose           Be verbose
-z, --silent            Be silent

-h, --help              Show this helptext

--                      No argument processing after this'''
	
	# defaults
	port = 9090
	# default to 0.0.0.0 for least astonishment. When you require that the
	# presentation is only accessible on localhost, you can probably figure
	# out that you can do that with '-a 127.0.0.1'.
	address = '0.0.0.0'
	verbose = 1
	single = False
	
	reveal_local = None	# path to local Reveal repository
	ovr_provider = False	# Override argument
	dont_attempt_local = False # whether or not to search for a local Reveal repository
	serve_local = True	# whether or not to serve a local Reveal repository
	
	# list wherein all the possible presentations get loaded during argument
	# parsing. After parsing, they get checked and loaded into the actual
	# presentation list
	maybe_list = []
	
	do_multiplex = False
	mconf_hash = hash.bcrypt
	
	# presenatation configuration object
	pconf = presentation.PConf()
	
	# continue parsing
	i = argn+1
	while i < len(argv):
		if argv[i] in ("-p", "--port"):
			port = int(argv[i+1])
			i += 1
		elif argv[i] in ("-a", "--addresses"):
			address = argv[i+1]
			i += 1 # skip the next argument
			
		elif argv[i] in ("-v", "--verbose"):
			verbose = 2
		elif argv[i] in ("-z", "--silent"):
			verbose = 0
			
		elif argv[i] in ("-s", "--single"):
			single = True
			
		elif argv[i] in ("-l", "--local"):
			reveal_local = find_local_reveal([argv[i+1]], False)
			i += 1
		elif argv[i] in ("-L", "--find-local"):
			reveal_local = find_local_reveal(list(hints), False)
		elif argv[i] in ("-d", "--dont-local"):
			dont_attempt_local = True
			serve_local = False
		elif argv[i] in ("-o", "--override"):
			temp = argv[i+1]
			
			if temp in presentation.Presentation.providers.keys():
				pconf.provider = temp
				i+=1	
		elif argv[i] in ("-n", "--no-local-route"):
			serve_local = False
		
		elif argv[i] in ("-m", "--multiplex"):
			do_multiplex = True
		
		elif argv[i] in ("--no-cache",):
			pconf.cache = False
		
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
	
	# if no local Reveal repository has been found, and we haven't been
	# forbidden to search for it, or serve it locally, attempt a search
	if not reveal_local and not dont_attempt_local:
		reveal_local = find_local_reveal(['/usr/bin/share/reveal.js'])
	

	if ovr_provider:
		print("Overriding Reveal.js providers with {} version".format(ovr_provider))


	# load the settings
	mconf = multiplex.MConf(htype = mconf_hash, rlen=multiplex.MConf.deflen) if do_multiplex else None

	pconf.mconf = mconf

	preslist = presentation.loadl(
			maybe_list,
			pconf,
			assoc = None,
			)
			

	# check if there are actually any valid presentations specified, abort if none	
	if len(preslist) == 0:
		print("No (valid) presentations specified")
		return False
	
	# only serve local presentations if a presentation actually needs them
	if presentation_need_locals(preslist):
		if reveal_local and os.path.exists(os.path.join(reveal_local, 'js/reveal.js')):
			print("Serving Reveal.js locally from ", reveal_local)
		elif serve_local:
			print("A presentation has 'local' configured as provider, but 'local' is not available")
			print("Your experience might be degraded, unless Reveal is served by another webserver under /reveal.js/")


	try:	
		run(	preslist, 
			address = address,
			port = port,
			single = single,
			verbosity = verbose,
			
			# only pass in the path to the local Reveal repository if it has
			# actually been found, and we are allowed to serve it locally
			local_reveal = reveal_local if (reveal_local and serve_local) else None,
			mconf = mconf,
			)
			
	except KeyboardInterrupt:
		print("Exiting")
		sys.exit(0)
		
##  @}
