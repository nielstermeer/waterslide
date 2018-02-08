# (C) 2017 Niels ter Meer
# This file is part of the WaterSlide presentation program
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
from sys import argv
import yaml
import json
import re
from datetime import datetime
from urllib.parse import urlparse
import sass
from collections import namedtuple
from waterslide import serve, multiplex, httputils
from email import utils
import base64

##
#  @defgroup presentation Presentation module
# 
#  @addtogroup presentation
#  @{
#

## dictionary of reveal plugins, and their associated objects
reveal_plugins = {
	# Interpret Markdown in <section> elements
	'marked':'{ "src": "{}/plugin/markdown/marked.js", "condition": function() { return !!document.querySelector( \'[data-markdown]\' ); } }',
	'markdown':'{ "src": "{}/plugin/markdown/markdown.js", "condition": function() { return !!document.querySelector( \'[data-markdown]\' ); } }',

	# Syntax highlight for <code> elements
	'highlight':'{ "src": "{}/plugin/highlight/highlight.js", "async": true, "callback": function() { hljs.initHighlightingOnLoad(); } }',

	# Zoom in and out with Alt+click
	'zoom':'{ "src": "{}/plugin/zoom-js/zoom.js", "async": true }',

	# Speaker notes
	'notes':'{ "src": "{}/plugin/notes/notes.js", "async": true }',
	# MathJax
	'math':'{ "src": "{}/plugin/math/math.js", "async": true }',
	'search': '{ "src": "{}/plugin/search/search.js" }',
	'print-pdf': '{ "src": "{}/plugin/print-pdf/print-pdf.js"}'
}

## Presentation configuration class
class PConf:
	
	def __init__(self,
		provider = None,
		mconf = None,
		cache = True,
		static = True,
	):
		self.provider = provider
		self.mconf = mconf
		self.cache = cache
		self.static = static
	
	def load(self, mconf):
		self.mconf = mconf
	
	helptext = '''
-o, --override <prov>   Override all configured presentation providers with
                        another provider. The availability of the new
                        provider is NOT checked.

--no-cache              Do not send caching headers

--disable-static        Disable static file routes, for when another webserver
                        is handling them for us
'''
	
	def parse(self, argn):
	
		if argv[argn] == "--no-cache":
			self.cache = False
			ret = 1
		elif argv[argn] in ("--disable-static",):
			self.static = False
			ret = 1
		elif argv[argn] in ("-o", "--override"):
			temp = argv[i+1]
			
			if temp in presentation.Presentation.providers.keys():
				self.provider = temp
				ret = 2
			else:
				ret = 1
		
		else:
			return 0
		return ret
		

## Exception thrown whenever there is an import error. Usually causes
#  the 'valid' member variable to be set to zero
class ImportError(Exception):
	def __init__(self, value = 'Import Error'):
		self.value = value
	def __str__(self):
		return repr(self.value)

## Main presentation class
# this class is where the rest of the program is build around. It represents
# the presentation which is stored on disk, while also performing operations
# transforming the data to a representable state. The specific functions are
# usually triggered by descendant classes, such as the HTTP_Presentation, which
# serves the presentation over html
class Presentation:
	
	## The presenation core
	html_base = ""
	## Source files modification time
	src_mtime = 0
	## Path to the presentation
	path = None
	## Whether or not this object should be considered valid
	valid = False
	
	## Presentation configuration dictionary
	config = {}
	## Configuration object
	conf = None
	
	## server config
	sconf = {}
	
	## list of providers
	providers = {
	"github": "https://raw.githubusercontent.com/hakimel/reveal.js/master",
	"cdnjs" : "https://cdnjs.cloudflare.com/ajax/libs/reveal.js/3.5.0",
	"local" : "/reveal.js"
	}
	
	provider = 'cdnjs'
	
	## The class constructor
	# @param self		The object pointer
	# @param path		The path to the presentation. Defaults to the current
	#			Working directory
	# @param ovr_provider	Override the configured provider with this argument.
	#			If not passed, or None or False, it will use either
	#			the configured provider or the default
	# @param multiplex	Multiplex configuration (None when not needed,
	#			an instance of multiplex.MConf)
	# @param cache		Whether to send caching headers or not
	def __init__(self, path = './', conf = None):
		
		self.conf = conf
		
		if not conf or not os.path.isdir(path):
			self.valid = False
			return

		self.path = os.path.realpath(path)
		
		self.try_import()
	
	def try_import(self):
		try:
			self.import_presentation()
			self.import_configuration()
			self.valid = True
		except ImportError as e:
			print(e)
			self.valid = False
	
	@property
	def basepath(self):
		return self.providers.get(self.provider) or self.providers['cdnjs']
	
	@property
	def isreal(self):
		return self.valid and os.path.isdir(self.path)
	
	## Get the mtimes of the source files which are used to build the
	#  presentation's html tree
	#
	# Currently the index file and the configuration file are checked
	@property
	def mtimes(self):
		fname = os.path.join(self.path, "index.html")
		cname = os.path.join(self.path, "conf.yaml")
		
		mtimes = []
		
		for f in (fname, cname):
			if os.path.exists(f):
				mtimes.append(os.path.getmtime(f))

		return max(mtimes)
		
		
	## import the presentation from disk
	# @param self	Object pointer
	# @param fname	Filename containing the html and settings of the presentation
	# @param separator	String separating the configuration from the markup in
	#			the presentation source
	#
	# It calls all the functions which are needed to build the presentation
	# it then stores the html inside an instance member, so that we don't have
	# to repeatedly call these functions
	def import_presentation(self, fname = "index.html", separator = "<!-- EOC -->"):
		
		path = os.path.join(self.path, fname)
		
		if not os.path.exists(path):
			raise ImportError('Presenatation source file does not exist')
		
		# Explicitly import as utf-8, as to prevent import errors when python
		# tries to import as ascii or something else.
		with open(path , mode="r", encoding="utf-8") as f:
		
			fctnt = f.read()
		
			conf_and_html = re.split(separator, fctnt, 1)
		
			self.src_mtime = self.mtimes
		
			if len(conf_and_html) == 2:
				self.config = self.parse_configuration(conf_and_html[0])

				self.provider = self.conf.provider or self.config.get('provider') or "cdnjs"
				self.html_base = conf_and_html[1]
			else:
				self.provider = self.conf.provider or "cdnjs"
				self.html_base = fctnt
	
	## Import the configuration file, if it exists
	# @param self	Object pointer
	def import_configuration(self):
		
		cfile = os.path.join(self.path, 'conf.yaml')
		
		if os.path.exists(cfile):
			with open(cfile, 'r') as f:
				self.sconf = self.parse_configuration(f.read())
	
	## Function which figures out the title
	# @param self	Object pointer
	# @return	The title
	#
	# It first checks for a title member in the configuration, and when that
	# fails, it defaults to the name of the directory
	@property
	def title(self):
		return self.config.get("title") or \
			 os.path.split(self.path)[-1]
	
	## Parse the presentation configuration
	# @param self		Object pointer
	# @param confstr	String containing the configuration, in YAML
	# @return		dictionary containing the configuration. On
	#			failure, it returns an empty dictionary
	#
	# If the library provider was not recognised, or not configured, it
	# defaults to cdnjs
	def parse_configuration(self, confstr):
		try:
			return yaml.load(confstr) or {}
		except yaml.YAMLError as exc:
			raise ImportError('Invalid yaml') from exc

	## Function which returns a string containing a link to a stylesheet
	# @param self		Object pointer
	# @param address	location of the stylesheet
	# @return		String which links to the stylesheet
	def link_stylesheet(self, address):
		return "<link rel=\"stylesheet\" href=\"{}\">".format(address)
	
	## Link a list of resources, using the given handler
	# @param self		Object pointer
	# @param handler	Function used to link the addresses
	# @param addresses	List of addresses, which need to be linked
	# @return		String containing all the linked resources
	def link_resources(self, handler, addresses):
		csss = ""
		for css in addresses:
			csss+= handler(css)
		
		return csss
			
	## Function which links a javascript resource
	# @param self		Object pointer
	# @param address	Location of the javascript resource
	# @return		String containing the link to the stylesheet
	def link_javascript(self, address):
		return "<script src=\"{}\"></script>".format(address)

	## Function which returns a string containing the links to all the
	#  required stylesheets
	# @param self	Object pointer
	# @return	String containing the links to the stylesheets
	@property
	def stylesheet_links(self):
		
		# stylesheets which are always needed. Default to black
		# if no stylesheet was specified
		csss = [self.basepath + "/css/reveal.css",		
			self.basepath + "/css/theme/{}.css" \
					.format(self.config.get("theme", "black"))]
		
		return self.link_resources(self.link_stylesheet, 
			csss + (self.config.get('styles') or []))
	
	## Dummy function
	#
	# This function get's overridden in HTTP_Presentation
	def do_multiplex(self, request):
		return False
	
	## Dummy function
	#
	# This function get's overridden in HTTP_Presentation
	def get_mdict(self, request):
		return {}
	
	## Get the Reveal.js initialisation json string
	# @param self		Object pointer
	# @param is_master	Whether or not the request currently being
	#			processed is allowed to be a master
	# @return		Reveal.js json initialisation string
	def reveal_init_json(self, request):
		
		# figure out which settings and plugin Reveal needs
		# to do multiplexing
		if self.do_multiplex(request):
			mult_json = {"multiplex": self.get_mdict(request)}
			m_plugins = [
				"{ src: '//cdn.socket.io/socket.io-1.3.5.js', async: true }",
				"{ src: '/waterslide/multiplex.js', async: true}"
				]
				
		else:
			mult_json = {}
			m_plugins = []
	
		init =	{**(self.config.get('init') or {}),
			 **{"dependencies":[]},
			 **mult_json,
			 }
			 
		initstr = json.dumps(init, ensure_ascii=False)
		
		# get the full list of plugins, including those needed for multiplexing
		plugin_list = [reveal_plugins.get(k) for k in (self.config.get('plugins') or [])] + m_plugins
		# add the basepath where necessary, and join them JSON style (with a comma)
		plugins = ','.join([k.replace('{}',self.basepath) 
					for k in plugin_list  or []])
		
		# brute force the insertion of javascript into the object
		return initstr.replace('"dependencies": []', "dependencies: [{}]".format(plugins))
	
	## Create miscellaneous head links
	@property
	def misc_head_links(self):
		return	"<link rel=\"shortcut icon\" href=\"{}\" />" \
			.format(self.config.get('favicon', '/waterslide/logo.png'))
	## Construct the html
	# @param self	Object pointer
	# @param base	The actual presentation
	# @return	The full html tree of the presentation
	#
	# This function combines all the functions which prepare bits
	# of the presentation, such as the link generators. It also adds the
	# the title in the head.
	def get_html(self, request = None):
	
		return str.join('',
			(
			"<!DOCTYPE html>",
			"<html><head><meta charset=\"utf-8\"/>",
			"<title>" + self.title + "</title>",
			self.stylesheet_links,
			self.misc_head_links,
			"</head><body>",
			"<div class=\"reveal\"><div class=\"slides\">",
			self.html_base,
			"</div></div>",
			self.link_resources(self.link_javascript, 
				(self.config.get('scripts') or []) +
				# only add head.js if we actually have plugins, or when we're multiplexing
				([self.basepath + "/lib/js/head.min.js"]
					if (	self.config.get('plugins') or 
						self.do_multiplex(request)) else []) +
				[self.basepath + "/js/reveal.js"]
				),				
			"<script>Reveal.initialize({});</script>".format(
					self.reveal_init_json(request)
				),
			"</body></html>",
			)
		)
	
	## Function which compiles a sass stylesheet
	# @param self	Object pointer
	# @param fname	File to compile
	# @return	The compiled
	def compile_sass(self, fname):
		return sass.compile(filename=fname)

## Descendant of the Presentation class, which handles presentations served over http
#
# This class handles the actions which are needed to serve a presentation over
# http. It compiles .scss style sheets on demand, it attempts to get the browser
# to cache the resources by sending the appropriate cache control headers (DAMN
# you, Firefox). It also reloads the presentation back into memory after the
# source file has changed.
#
# To keep it as framework agnostic as possible, the common_handler() method
# uses HTTP_Request named tuples. Also, the urls passed to it should be rewritten
# to be relative to the presentation's directory
#
# consider /foo/bar.js within the foo presentation. The url which is then
# passed to the foo object should be 'bar.js'.
class HTTP_Presentation(Presentation):
	
	## Multiplex configuration which will be send to Reveal
	mult_randomness = None
	mult_nosession = None
	
	## Wrapper init function. Calls parent init first, then initialises multiplexing
	def __init__(self, *args, **kwargs):
		
		super().__init__(*args, **kwargs)
		
		self.setup_multiplex()
	
	## Get the slug, to be used in the url
	# @param self	Object pointer
	# @return	Slug to be used in the url
	#
	# The slug is always based upon the directory the presentation it is
	# stored in. For the serve subcommand, it doesn't really matter where
	# the slug comes from (this is because it knows where all the
	# presentations are, because they are named on the commandline, and
	# can then deduce the slug from either the directory name or from the
	# settings)
	#
	# The manage subcommand cannot do this, since it initialises the
	# presentations on demand. The only way it can then satisfy the request
	# is to map the requested presentation path onto the file system, and
	# then initialising the presentation located there. There is as such
	# no way to use slugs based upon the title.
	@property
	def slug(self):
		return  os.path.split(self.path)[-1]
	
	## Multiplex initialisation method
	# @param self	Object pointer
	#
	# this method gathers randomness for the secret and the socket-Id
	#
	# The mult_nosession randomness is used for when no session is provided,
	# as in "/?master" vs "/?master=foo".
	def setup_multiplex(self):
		
		rlen = self.conf.mconf.rlen
		
		self.mult_randomness	= multiplex.getrandom(rlen)
		self.mult_nosession	= multiplex.getrandom(6)
	
	## Check if a request is allowed to get multiplexing configuration
	# @param self		Object pointer
	# @param request	Request being processed
	def do_multiplex(self, request):
		
		# Do nothing if we arent processing a request
		if not request:
			return False
		
		master = request.url.query.get('master')
		slave  = request.url.query.get('slave')
		
		lmconf = self.sconf.get('multiplex', {})

		# Multiplexing is disabled
		if self.conf.mconf.do_multiplex == False and lmconf.get('enable') != True:
			return False
		
		# Client is not a master
		if master != None:
			return True
		
		# Client specifically requested to be a slave
		if slave != None:
			return True
		
		# autoslaving is disabled
		if self.conf.mconf.autoslave == False or lmconf.get('autoslave') != True:
			return False
		# autoslave any client which isn't a master, since autoslaving
		# is enabled
		else:
			return True
	
	## Reload the presentation into memory, if it needs to be reloaded
	# @param self	Object pointer
	def reload(self):
		
		if self.mtimes != self.src_mtime:
			print("Change detected")
			self.try_import()			
	
	## Get the multiplexing session name
	# @param self	Object pointer
	# @param request	Request being processed
	# @param default	Default session name. Can be used to return a
	# 			signalling value instead of the default
	#			session name when no session is provided
	def get_session_name(self, request, default = None):
		default = self.mult_nosession if default in ('', None) else default
		
		return 		request.url.query.get('master') or \
				request.url.query.get('slave') or \
				default
	
	## Create a multiplexing dictionary
	def get_mdict(self, request):
		
		master = request.url.query.get('master')
		session = self.get_session_name(request)
		
		secret = self.mult_randomness + session
		
		return { # only pass the secret onto the master presentation(s)
			'secret': secret if master != None else None,
			'id': self.conf.mconf.htype.encrypt(secret),
			'url': self.conf.mconf.MX_server
		}
	
	## Figure out the handler needed to process the current request
	# @param self		Object pointer
	# @param request	Request currently being processed
	# @param url		urlparse()-ed url
	# @return	Function pointer, or None on failure
	#
	# It figures out the request handler based upon the url, and the
	# the extension of the url
	def figure_handler(self, path):
			
		if path == "":
			return self.send_html
		elif os.path.exists(os.path.join(self.path, path)):
			
			ext = os.path.splitext(path)[1]
			
			if ext == ".scss":
				return self.send_sass
			else:
				return self.send_direct
		else:
			return self.send_notfound
	
	## Request entry point method
	# @param self		Object pointer
	# @param request	Request currently being processed (HTTP_Request tuple)
	#
	# This function is the main entry point for any request with its url
	# being within the presentation root. The path must be normalised to
	# be relative to the presentation root. It accepts only HTTP_Request
	# tuples as its request type, so we can keep this class as framework
	# agnostic as possible.
	@httputils.aio_translate(rewrite = lambda r:r.match_info['tail'],
					logger = httputils.log_request)
	def handle(self, request):
	
		return (self.figure_handler(request.url.path))(request.url.path, request)
		
	## Request handler for sending files directly from disk
	# @param self		Object pointer
	# @param path		Path to the file being requested, relative to
	#			the presentation root
	# @param request	Request object. Is not used in this function,
	#			but is used in utility functions. This parameter
	#			should not be processed directly in this function
	#			as to maintain compatability with possibly other
	#			webservers.
	# @return		A HTTP_Response named tuple
	def send_direct(self, path, request):
		
		if self.conf.static == False:
			return httputils.HTTP_Response(
				code = 403,
				headers = {},
				body = 'WaterSlide static routes have been disabled'
				)
		
		fname = os.path.join(self.path, path)
	
		cached = httputils.client_has_cached(fname, request, self.conf.cache)
	
		if cached.code == 304:
			return cached
		
		with open(fname, 'rb') as f:
			ctnt = f.read()
		
		return httputils.HTTP_Response(code = 200, headers = cached.headers, body = ctnt)

	## Request handler for sass/scss stylesheets
	# @copydetails HTTP_Presentation.send_direct
	def send_sass(self, path, request):
	
		fname = os.path.join(self.path, path)
	
		cached = httputils.client_has_cached(fname, request, self.conf.cache)
		if cached.code == 304:
			return cached
		
		ctnt = self.compile_sass(fname)
		
		return httputils.HTTP_Response(
			code = 200, 
			headers = {
				**cached.headers,
				'Content-type':'text/css'
				},
			body = ctnt
			)
	
	## Request handler for when a resource is not found
	# @copydetails HTTP_Presentation.send_direct
	def send_notfound(self, path, request):
		return httputils.HTTP_Response(
			code = 404, 
			headers = {},
			body = "404 Not Found:\n{}".format(path)
			)
	
	## Authorise requests to be a master of a presentation
	# @param self		Object pointer
	# @param request	Request being authorised
	def authorise(self, request):

		master = request.url.query.get('master')
		
		session = self.get_session_name(request, None)
		
		if master == None:
			return httputils.HTTP_Response(code = 200, headers = {}, body = '')
		
		auth = httputils.decode_basic_auth(request.headers.get('Authorization'))
		stored = self.sconf.get('multiplex', {}).get('auth')
		
		if stored:
			local = httputils.basicauth(uname = stored.get('uname'),
						passwd = stored.get('passwd'))
		else:	# send okay if no credentials have been defined
			return httputils.HTTP_Response(code = 200, headers = {}, body = '')
		
		if auth == local:
			return httputils.HTTP_Response(code = 200, headers = {}, body = '')
		else:
			return httputils.HTTP_Response(
				code = 401,
				headers = {
					'WWW-Authenticate': 'Basic realm={} {}'
						.format(self.title, session),
					},
				body = ''
			)
		

	## Request handler for the html presentation source
	# @copydetails HTTP_Presentation.send_direct
	#
	# This method also check whether or not the source file has changed,
	# and it reloads it when necessary
	def send_html(self, url, request):
		
		fname = os.path.join(self.path, "index.html")
		
		self.reload()

		# only cache the html when we're not multiplexing
		if not self.do_multiplex(request):
			cached = httputils.client_has_cached(fname, request, do_cache = self.conf.cache, mtime = self.mtimes)
			if cached.code == 304:
				return cached
		else:
			auth = self.authorise(request)
			if auth.code == 401:
				return auth
			
			cached = httputils.HTTP_Response(code = 200, headers = {}, body = "")
		
		return httputils.HTTP_Response(
			code = 200, 
			headers = {
				**cached.headers,
				'Content-type':'text/html'
				},
			body = self.get_html(request)
			)

class managed_pres(HTTP_Presentation):
	
	def handle(self, request):
		return self.send_html('', request)

## load a list of paths which might be presentations into a dictionary or list, depending on the assoc arg
#
# @param l		List to be checked and loaded
# @param conf		Presentation configuration
# @param ptype		Presentation type to initialise
# @param assoc		To associate the object with something, and if so, what (currently recognised
# 			are "slug" and "title"
def loadl(l, conf, ptype = HTTP_Presentation, assoc = None):
	if assoc == None:
		preslist = []
	else:
		preslist = {}
	
	for presentation_path in l:
		obj = ptype(presentation_path, conf)
		
		if obj.isreal:
			if assoc == "slug":
				preslist[obj.assoc] = obj
			elif assoc == "title":
				preslist[obj.title] = obj
			else:
				preslist.append(obj)
	
	return preslist

## @}
