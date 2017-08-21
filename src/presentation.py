import os
import yaml
import json
import re
from datetime import datetime
from urllib.parse import urlparse
import sass
import serve

##
#  @defgroup presentation Presentation module
# 
#  @addtogroup presentation
#  @{
#

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
	
	## list of providers
	providers = {
	"github": "https://raw.githubusercontent.com/hakimel/reveal.js/master",
	"cdnjs" : "https://cdnjs.cloudflare.com/ajax/libs/reveal.js/3.5.0"
	}
	
	## default library provider
	basepath = providers["cdnjs"]
	
	## The class constructor
	# @param self	The object pointer
	# @param path	The path to the presentation. Defaults to the current
	#		Working directory
	def __init__(self, path = './'):
	
		if not os.path.isdir(path):
			self.isreal = False
			return
	
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
				self.html = self.prepare_html(conf_and_html[1])
			else:
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
			conf = yaml.load(confstr) or {}
			
			# cdnjs is the default provider
			provider = conf.get('provider', 'cdnjs')
			
			if provider not in self.providers.keys():
				print("Library provider not recognised: ", provider)
				key = "cdnjs"				
			else:
				key = provider
			
			self.basepath = self.providers[key]
			
			return conf
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
		return json.dumps(self.config.get('init') or {}, ensure_ascii=False)
	
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
				[self.basepath + "/js/reveal.js"]),
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
		return self.title().lower().replace(' ', '-')
	
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
	def client_has_cached(self, request, filename):
		
		LM = datetime.utcfromtimestamp(os.path.getmtime(filename)) \
			.strftime('%a, %d %b %Y %H:%M:%S GMT')
		
		if request.headers.get('If-Modified-Since') == LM:
			request.send_response(304)
			request.send_header("Cache-Control", "must-revalidate")
			request.end_headers()
			return True
		else:
			request.send_response(200)
			request.send_header("Cache-Control", "must-revalidate")
			request.send_header("Last-Modified", LM)
			return False
			
	## Figure out the handler needed to process the current request
	# @param self		Object pointer
	# @param request	Request currently being processed
	# @param url		urlparse()-ed url
	# @return	Function pointer, or None on failure
	#
	# It figures out the request handler based upon the url, and the
	# the extension of the url
	def figure_handler(self, request, url):
			
		if url.path == "":
			return self.send_html
		elif os.path.exists(os.path.join(self.path, url.path)):
			
			ext = os.path.splitext(url.path)[1]
			
			if ext == ".scss":
				return self.send_sass
			else:
				return self.send_direct
		else:
			return None
	
	## Request entry point method
	# @param self		Object pointer
	# @param request	Request currently being processed
	# @param rurl		Request url, pre-processed to be relative to the
	#			presentation root
	#
	# This function is the main entry point for any request with its url
	# being within the presentation root.
	#
	# It changes the protocol version to HTTP/1.1, and then calls either
	# the request handler, or the notfound handler, depending upon whether
	# a handler and source file could be found
	#
	# It requires that the path of the url being processed to be relative
	# to the document root, and that the source file of the request is
	# within the presentation root.
	#
	# Consider the request http://baz.nl/foo/bar.scss, of the 'foo'
	# presentation. The request should then be preprocessed to
	# http://baz.nl/bar.scss. This is to ensure that this class can be used
	# either with one presentation, with all the files of the presentation
	# root mapping to files in the "documen root", or with several
	# presentation, with each presentation having its own subdirectory.
	def handle(self, request, rurl):
	
		url = urlparse(rurl)
		
		f = self.figure_handler(request, url)
		
		request.protocol_version = 'HTTP/1.1'
		
		if f:
			f(request, url)
		else:
			request.notfound()

	## Request handler for sending files directly from disk
	# @param self		Object pointer
	# @param request	Request currently being considered
	# @param url		urlparse()-d url object
	def send_direct(self, request, url):
		
		fname = os.path.join(self.path, url.path)
	
		if self.client_has_cached(request, fname):
			return
			
		request.end_headers()
		
		with open(fname, 'r') as f:
			request.wfile.write(bytes(f.read(), "utf8"))

	## Request handler for sass/scss stylesheets
	# @copydetails HTTP_Presentation.send_direct
	def send_sass(self, request, url):
	
		fname = os.path.join(self.path, url.path)
	
		if self.client_has_cached(request, fname) :
			return
		
		request.send_header('Content-type','text/css')
		request.end_headers()
		request.wfile.write(bytes(self.compile_sass(fname), "utf8"))
	
	## Request handler for when a resource is not found
	# @copydetails HTTP_Presentation.send_direct
	def send_notfound(self, request, url):
		serve.notfound(request, url)

	## Request handler for the html presentation source
	# @copydetails HTTP_Presentation.send_direct
	#
	# This method also check whether or not the source file has changed,
	# and it reloads it when necessary
	def send_html(self, request, url):
		
		fname = os.path.join(self.path, "index.html")
		
		if os.path.getmtime(fname) != self.html_mtime:
			self.reload()
		
		if self.client_has_cached(request, fname) :
			return

		request.send_header('Content-type','text/html')
		request.end_headers()
		request.wfile.write(bytes(self.html, "utf8"))

## list of presentation this instance of the program serves
listof = {}

## @}
