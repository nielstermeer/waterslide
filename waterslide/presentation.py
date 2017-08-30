import os
import yaml
import json
import re
import pytz
from datetime import datetime
from urllib.parse import urlparse
import sass
from collections import namedtuple
from aiohttp import web
from waterslide import serve, multiplex
from email import utils

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

class PConf:
	
	def __init__(self,
		provider = None,
		mconf = None,
		cache = True,
	):
		self.provider = provider
		self.mconf = mconf
		self.cache = cache
		

## Main presentation class
# this class is where the rest of the program is build around. It represents
# the presentation which is stored on disk, while also performing operations
# transforming the data to a representable state. The specific functions are
# usually triggered by descendant classes, such as the HTTP_Presentation, which
# serves the presentation over html
class Presentation:
	
	## The presenation core
	html_base = ""
	## Path to the presentation
	path = None
	## Whether or not this object should be considered valid
	isreal = False
	
	## Presentation configuration dictionary
	config = {}
	## Configuration object
	conf = None
	
	## Multiplex configuration which will be send to Reveal
	mult_conf = {}
	
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
			self.isreal = False
			return

		self.path = os.path.realpath(path)
		
		if self.conf.mconf:
			self.mult_conf = multiplex.create_multiplex_dict(self.conf.mconf)
		
			
		self.import_presentation()
		self.isreal = True		
	
	@property
	def basepath(self):
		return self.providers.get(self.provider) or self.providers['cdnjs']
	
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
		with open(os.path.join(self.path, fname) , 'r') as f:
		
			fctnt = f.read()
		
			conf_and_html = re.split(separator, fctnt, 1)
		
			self.html_mtime = os.path.getmtime(os.path.join(self.path, "index.html"))
		
			if len(conf_and_html) == 2:
				self.config = self.parse_configuration(conf_and_html[0])

				self.provider = self.conf.provider or self.config.get('provider') or "cdnjs"
				self.html_base = conf_and_html[1]
			else:
				self.provider = self.conf.provider or "cdnjs"
				self.html_base = fctnt
				
	
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
			print(exc)
			return {}

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
	
	## Get the Reveal.js initialisation json string
	# @param self		Object pointer
	# @param is_master	Whether or not the request currently being
	#			processed is allowed to be a master
	# @return		Reveal.js json initialisation string
	def reveal_init_json(self, is_master = False):
	
		# figure out which settings and plugin Reveal needs
		# to do multiplexing
		if self.conf.mconf:
			mult_json = {"multiplex": self.mult_conf}
			m_plugins = [
				"{ src: '//cdn.socket.io/socket.io-1.3.5.js', async: true }",
				"{ src: '/waterslide/multiplex.js', async: true}"
				]
			
			# only pass the secret onto the master presentation(s)
			if not is_master:
				mult_json['secret'] = None
			
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
	
	## Construct the html
	# @param self	Object pointer
	# @param base	The actual presentation
	# @return	The full html tree of the presentation
	#
	# This function combines all the functions which prepare bits
	# of the presentation, such as the link generators. It also adds the
	# the title in the head.
	def get_html(self, is_master = False):
	
		return str.join('',
			(
			"<!DOCTYPE html>",
			"<html><head><meta charset=\"utf-8\"/>",
			"<title>" + self.title + "</title>",
			self.stylesheet_links,
			"</head><body>",
			"<div class=\"reveal\"><div class=\"slides\">",
			self.html_base,
			"</div></div>",
			self.link_resources(self.link_javascript, 
				(self.config.get('scripts') or []) +
				# only add head.js if we actually have plugins, or when we're multiplexing
				([self.basepath + "/lib/js/head.min.js"] if (self.config.get('plugins') or self.conf.mconf) else []) +
				[self.basepath + "/js/reveal.js"]
				),				
			"<script>Reveal.initialize({});</script>".format(
					self.reveal_init_json(is_master)
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

## Named tuple used to abstract the framework's way of representing the response to a request. 
#
# Used in the request handlers, after which the request entrypoint converts
# it to the framework's response representation. This is so that we don't have
# to rewrite any of the request handlers whenever we change frameworks
HTTP_Response	= namedtuple('HTTP_Response',	('code', 'headers', 'body'))

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

	## Last measured modification time of the source html file
	html_mtime = 0

	## Get the slug, to be used in the url
	# @param self	Object pointer
	# @return	Slug to be used in the url
	@property
	def slug(self):
		return self.title.lower().replace(' ', '-')
	
	## Reload the presentation into memory
	# @param self	Object pointer
	def reload(self):
		print("Change detected")
		self.import_presentation()

	## Check whether the client has the resource cached, and send the appropriate headers
	# @param self		Object pointer
	# @param request	The request currently being processed
	# @param filename	Source file of the request
	# @return		Boolean if the the client has the resource cached,
	#			so that the calling function knows what to do further
	def client_has_cached(self, filename, request):
	
		# decode the last modified header here instead of relying on
		# a specific implementation which decodes it for us
		imsp = datetime(
			*utils.parsedate(
				request.headers.get(	'if-modified-since',
							'Thu, 1 Jan 1970 00:00:00 GMT'
						)
					)[:6]
			).replace(tzinfo=pytz.utc)
		
		# strip of the microseconds, so we can compare the objects without having to round.
		lm = datetime.utcfromtimestamp(os.path.getmtime(filename)).replace(tzinfo=pytz.utc, microsecond = 0)
		
		if self.conf.cache and imsp == lm:
		
			return HTTP_Response(
				code = 304, 
				headers = {
					"Cache-Control":"must-revalidate"
					} if self.conf.cache else {},
				body = ""
				)
		else:			
			return HTTP_Response(
				code = 200, 
				headers = {
					"Cache-Control":"must-revalidate",
					"Last-Modified": lm.strftime('%a, %d %b %Y %H:%M:%S GMT')
					} if self.conf.cache else {},
				body = ""
				)
			
			
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
	
	## Log a request to stdout
	# @param self		Object pointer
	# @param request	Request object of the framework
	# @param response	HTTP_Response named tuple
	def log_request(self, request, response):
	
		# build a query string from a dictionary
		def build_query_string(d):
			return '?' + '&'.join([qstr(e, d[e]) for e in d.keys()]) if len(d) else ''
		
		# build a query substring correctly
		def qstr(a, b):
			return '{}={}'.format(a,b) if b else a
	
		print("HTTP/{}.{} {} {} {}".format(
			request.version.major, request.version.minor,
			response.code,
			request.method,
			'{}//{}/{}{}'.format(*request.url[:3], build_query_string(request.url.query))
			)
		)
	
	## Request entry point method
	# @param self		Object pointer
	# @param request	Request currently being processed (HTTP_Request tuple)
	#
	# This function is the main entry point for any request with its url
	# being within the presentation root. The path must be normalised to
	# be relative to the presentation root. It accepts only HTTP_Request
	# tuples as its request type, so we can keep this class as framework
	# agnostic as possible.
	def handle_common(self, request):
	
		response = (self.figure_handler(request.url.path))(request.url.path, request)
		
		# print out logmessage
		self.log_request(request, response)
		
		return response
		
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
		
		fname = os.path.join(self.path, path)
	
		cached = self.client_has_cached(fname, request)
	
		if cached.code == 304:
			return cached
		
		with open(fname, 'rb') as f:
			ctnt = f.read()
		
		return HTTP_Response(code = 200, headers = cached.headers, body = ctnt)

	## Request handler for sass/scss stylesheets
	# @copydetails HTTP_Presentation.send_direct
	def send_sass(self, path, request):
	
		fname = os.path.join(self.path, path)
	
		cached = self.client_has_cached(fname, request)
		if cached.code == 304:
			return cached
		
		ctnt = self.compile_sass(fname)
		
		return HTTP_Response(
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
		return HTTP_Response(
			code = 404, 
			headers = {},
			body = "404 Not Found:\n{}".format(path)
			)

	## Request handler for the html presentation source
	# @copydetails HTTP_Presentation.send_direct
	#
	# This method also check whether or not the source file has changed,
	# and it reloads it when necessary
	def send_html(self, url, request):
		
		fname = os.path.join(self.path, "index.html")
		
		if os.path.getmtime(fname) != self.html_mtime:
			self.reload()
		
		# only cache the html when we're not multiplexing
		if not self.conf.mconf:
			cached = self.client_has_cached(fname, request)
			if cached.code == 304:
				return cached
		else:
			cached = HTTP_Response(code = 200, headers = {}, body = "")
	
		return HTTP_Response(
			code = 200, 
			headers = {
				**cached.headers,
				'Content-type':'text/html'
				},
			body = self.get_html(True if request.url.query.get('master') != None else False)
			)

HTTP_URL	= namedtuple('HTTP_URL',	('scheme', 'host', 'path', 'query'))
HTTP_Request	= namedtuple('HTTP_Request', 	('version', 'method', 'headers', 'url','body', 'parent_object'))

## Class to act as a middleware to convert back and forth between aiohttp's
#  representation of a request and a response to the one used by the
#  parent class (HTTP_Presentation)
class aiohttp_presentation_middleware(HTTP_Presentation):

	def handle(self, request):
		
		# convert the aiohttp request object to a HTTP_Request tuple
		# so that it can be processed by the HTTP_Presentation class
		r = HTTP_Request(
			version = request.version,
			method = request.method,
			headers = request.headers,
			url = HTTP_URL(
				scheme	= request.scheme,
				host	= request.host,
				# url relative to the presentation directory
				path	= request.match_info['tail'],
				query	= request.query,
			),
			body = request.read(),
			parent_object = request
		)
		
		R = self.handle_common(r)
		
		return web.Response(
			status  = R.code,
			headers = R.headers,
			body    = R.body,
		)
		
		

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
		obj = ptype(
			presentation_path,
			conf
			)
		if obj.isreal:
			if assoc == "slug":
				preslist[obj.assoc] = obj
			elif assoc == "title":
				preslist[obj.title] = obj
			else:
				preslist.append(obj)
	
	return preslist

## @}
