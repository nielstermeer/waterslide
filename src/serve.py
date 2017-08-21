from http.server import BaseHTTPRequestHandler, HTTPServer
import sys
import presentation
import re
from urllib.parse import urlparse, urlunparse

##
#  @defgroup serve HTTP server module
# 
#  @addtogroup serve
#  @{
#

## Function which strips an arbitrary string of the front of another string
## currently used to strip of the presentation directory of a path
def strip_presentation_root(root, path):
	return re.sub(root, '', path, 1)


## Convert the request url to a url which can be used in the presentation
## classes
def convert_path(root, urll):
	urlll = list(urll)
	
	# the second element corresponds to <url-obj>.path
	urlll[2] = strip_presentation_root(root, urll.path)
	return urlunparse(urlll)
	

## Base presentation request handler
#
# Class which holds all the function and state shared between the single-, and
# multiple presentation handlers
class base_presentation(BaseHTTPRequestHandler):
	
	## Send the 404 headers and error message
	# @param request	Request being processed
	def notfound(request):
		request.send_response(404)
		request.end_headers()
		request.wfile.write(bytes(
			"Error 404\n\nresource: \"{}\"\nwas not found on this server"
				.format(request.path),
			"utf8")
		)

## Class which is used when only a single presentation is to be served from
# the document root directory. Since it is the only one, it does not need
# a presentation lookup function
class single_presentation(base_presentation):

	## GET request handler
	# @param self	Object pointer
	def do_GET(self):
		url = convert_path('/', urlparse(self.path))		
		presentation.listof.handle(self, url)


## Class which is used to serve multiple presentations.
# It builds up a routing table by asking the presentation objects for their
# slugs, which then get used in the url as the directory
class multiple_presentations(base_presentation):

	## Redirect user agent to the actual presentation location
	# @param self		Object pointer
	# @param location	Presentation slug, without leading/trailing slashed
	def redirect_to_real(self, location):	
		self.send_response(301)
		self.send_header("Location", '/' + location + '/')
		self.end_headers()

	## GET request handler
	# @param self	Object pointer
	#
	# It parses the request url, and the does a lookup for the presentation
	# which was requested. It triggers a redirect when the user agent
	# requested the file instead of the directory for the presentation,
	# and triggers a 404 when the request does not correspond to any known
	# presentation
	def do_GET(self):
		
		url = urlparse(self.path)
		path = re.split('/', url.path)
		name = path[1]
		
		# strip of the presentation path, so the presentation class
		# can search within that url for its files
		converted_url = convert_path('/' + name + '/', url)
		
		if name:
			obj = presentation.listof.get(name)
			
			# redirect if url is wrong (as in, tried to acces file
			# instead of directory), but presentation exists
			if len(path) == 2 and obj:
				self.redirect_to_real(name)
			
			# if the url is correct and the object exists, serve it
			elif obj:
				self.slug = name
				self.obj = obj
				obj.handle(self, converted_url)
			
			# return 404
			else:
				self.notfound()
		else:
			self.notfound()

## Build a routing table for the webserver from a list of presentation objects
# @param preslist	List of presentations to be served
# @return		Lookup table of presentations
# We ask the presentation for its slug, which we then use for the route
def build_routing_table(preslist):
	presdict = {}
	for i in preslist:
		presdict[i.slug()] = i
	
	return presdict

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
'''
Serve subcommand: Serve a presentation over HTTP

Usage:
serve [options] [presentations]

Options:
-p, --port         Port for the webserver to listen to (p<1024 requires root)
-a, --addresses    Addresses to listen to (0.0.0.0 is the whole accessible
                   internet, 127.0.0.1 is only your own computer)
-s, --single       Serve a single presentation in its own directory, instead
                   of directly in the root directory
-v, --verbose      Be verbose
-h, --help         Show this helptext
'''
	
	
	# defaults
	port = 9090
	addresses = '127.0.0.1'
	# Serve a single presentation in its own directory. If set it overrides
	# the default that a single presentation will be served from the
	# document root
	single_presentation_as_directory = False
	verbose = False
	
	# continue parsing
	i = argn+1
	while i < len(argv):
		if argv[i] in ("-p", "--port"):
			port = int(argv[i+1])
		if argv[i] in ("-a", "--addresses"):
			addresses = argv[i+1]
		if argv[i] in ("-s", "--single"):
			single_presentation_as_directory = True
		if argv[i] in ("-v", "--verbose"):
			verbose = True
		if argv[i] in ("-h", "--help"):
			print(helptext)
			return
		else:
			obj = presentation.HTTP_Presentation(argv[i])
			if obj.isreal:
				preslist.append(obj)
			
		i += 1

	number_of_presentations = len(preslist)

	# if we've got more than one presentation, or if we want to serve
	# one presentation through a subdirectory instead of through the
	# document root, serve the presentation(s) using a routing table
	if number_of_presentations > 1 or \
	  (number_of_presentations == 1 and single_presentation_as_directory):
		presentation.listof = build_routing_table(preslist)
		handler = multiple_presentations 
	
	# if we've got just one presentation, serve it directly
	elif number_of_presentations == 1:
		presentation.listof = preslist[0]
		handler = single_presentation
	else:
		print("No presentations specified")
		return False
	
	# status output section
	print("Serving {} presentation{}, titled:".format(
		number_of_presentations,
		"s" if number_of_presentations > 1 else "") # handle plurals
	)
	
	# prepare the lambda functions for verbose output
	if not verbose:
		of = lambda obj: "" # nothing gets added to status string
	else:
		# if verbose, show the url it is served under and 
		# the presentation source
		if handler == single_presentation:
			of = lambda obj: " (url: {} source: '{}')" \
					.format('/', obj.path)
		else:
			of = lambda obj: " (url: {:<15} source: '{}')"	\
					.format('/' + obj.slug() + '/', obj.path)
	
	for i in preslist:
		print(" - {:<15}{}".format('"' + i.title() + '"', of(i)))
		
	print("on {}:{}".format(addresses, port))
	# </> status output section

	try:
		server = HTTPServer((addresses, port), handler)
		server.serve_forever()
	except KeyboardInterrupt:
		print("Exiting")
		sys.exit(0)
		
##  @}
