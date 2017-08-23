import os
import yaml
import json
import re
import pytz
from datetime import datetime
from urllib.parse import urlparse
import sass
import serve
from collections import namedtuple
from aiohttp import web

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


## Main presentation class
# this class is where the rest of the program is build around. It represents
# the presentation which is stored on disk, while also performing operations
# transforming the data to a representable state. The specific functions are
# usually triggered by descendant classes, such as the HTTP_Presentation, which
# serves the presentation over html
class Presentation:
	
	## html which is send upon a request
	html = "" 
	## Path to the presentation
	path = None
	## Whether or not this object should be considered valid
	isreal = False
	## Configuration dictionary
	config = {}
	##
	ovr_provider = None
	
	## list of providers
	providers = {
	"github": "https://raw.githubusercontent.com/hakimel/reveal.js/master",
	"cdnjs" : "https://cdnjs.cloudflare.com/ajax/libs/reveal.js/3.5.0",
	"local" : "/reveal.js"
	}
	
	## default library provider
	basepath = providers["cdnjs"]
	
	## The class constructor
	# @param self		The object pointer
	# @param path		The path to the presentation. Defaults to the current
	#			Working directory
	# @param ovr_provider	Override the configured provider with this argument.
	#			If not passed, or None or False, it will use either
	#			the configured provider or the default
	def __init__(self, path = './', ovr_provider = None):
	
		if not os.path.isdir(path):
			self.isreal = False
			return

		if ovr_provider:
			self.ovr_provider = ovr_provider

		self.path = os.path.realpath(path)		
		self.import_presentation()
		self.isreal = True
	
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

				self.set_provider(
					self.ovr_provider or self.config.get('provider') or "cdnjs"
				)
				
				self.html = self.prepare_html(conf_and_html[1])
			else:
				self.set_provider(self.ovr_provider or "cdnjs")
				self.html = self.prepare_html(fctnt)
				
	
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
	
	def set_provider(self, provider):
		if provider not in self.providers.keys():
			print("Library provider not recognised: ", provider)
			key = "cdnjs" # cdnjs is the default provider			
		else:
			key = provider
		
		self.basepath = self.providers[key]
	
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
	# @param self	Object pointer
	# @return	Reveal.js json initialisation string
	@property
	def reveal_init_json(self):
	
		init = {**(self.config.get('init') or {}), **{"dependencies":[]}}
		initstr = json.dumps(init, ensure_ascii=False)
		
		# get a string containing the plugin objects, separated by commas
		# add the basepath
		plugins = ','.join([reveal_plugins.get(k, "").replace('{}',self.basepath) 
					for k in self.config.get('plugins') or []])
		
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
	def prepare_html(self, base):
	
		return str.join('',
			(
			"<!DOCTYPE html>",
			"<html><head><meta charset=\"utf-8\"/>",
			"<title>" + self.title + "</title>",
			self.stylesheet_links,
			"</head><body>",
			"<div class=\"reveal\"><div class=\"slides\">",
			base,
			"</div></div>",
			self.link_resources(self.link_javascript, 
				(self.config.get('scripts') or []) +
				# only add head.js if we actually have plugins
				([self.basepath + "/lib/js/head.min.js"] if (self.config.get('plugins')) else []) +
				[self.basepath + "/js/reveal.js"]
				),				
			"<script>Reveal.initialize({});</script>".format(
					self.reveal_init_json
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
		
		lm = datetime.utcfromtimestamp(os.path.getmtime(filename)).replace(tzinfo=pytz.utc)
		
		if request.if_modified_since != None and \
			request.if_modified_since.replace(tzinfo=pytz.utc) < lm.replace(tzinfo=pytz.utc):
		
			return HTTP_Response(
				code = 304, 
				headers = {
					"Cache-Control":"must-revalidate"
					},
				body = ""
				)
		else:			
			return HTTP_Response(
				code = 200, 
				headers = {
					"Cache-Control":"must-revalidate",
					"Last-Modified": lm.strftime('%a, %d %b %Y %H:%M:%S GMT')
					},
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
		print("HTTP/{}.{} {} {} {}".format(
			request.version.major, request.version.minor,
			response.code,
			request.method,
			request.url))
	
	## Request entry point method
	# @param self		Object pointer
	# @param request	Request currently being processed
	#
	# This function is the main entry point for any request with its url
	# being within the presentation root.
	def handle(self, request):
		
		# if the request path is just the slug, without the directory
		# at the end, redirect it to the directory
		if request.path == '/' + self.slug:
			self.log_request(request, 
				HTTP_Response(
					code = 304, 
					headers = {"Location": '/' + self.slug + '/'},
					body = None
				)
			)
			
			return web.HTTPFound('/' + self.slug + '/')			

		# generate the path relative to the presentation root, stripping
		# of the root directory and the slug. If we do them both at the
		# same time, while we serve the presenation as document root, it
		# will not strip of the leading slash, which then causes the
		# server to return 500
		lpath = request.path.replace('/', '', 1).replace(self.slug + '/', '', 1)
		r = (self.figure_handler(lpath))(lpath, request)
		
		# print out logmessage
		self.log_request(request, r)
		
		return web.Response(
			status  = r.code,
			headers = r.headers,
			text    = r.body,
		)
		
		
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
		
		with open(fname, 'r') as f:
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
		
		cached = self.client_has_cached(fname, request)
		if cached.code == 304:
			return cached
	
		return HTTP_Response(
			code = 200, 
			headers = {
				**cached.headers,
				'Content-type':'text/html'
				},
			body = self.html
			)

## @}
