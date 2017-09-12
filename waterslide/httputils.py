# (C) 2017 Niels ter Meer
# This file is part of the WaterSlide presentation program
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from datetime import datetime
import pytz
import os
from aiohttp import web
from email import utils
from collections import namedtuple
from waterslide import multiplex
import base64

##
#  @defgroup httputils HTTP related utility functions/classes/definitions
# 
#  @addtogroup httputils
#  @{
#

## Named tuple used to abstract the framework's way of representing the response to a request. 
#
# Used in the request handlers, after which the request entrypoint converts
# it to the framework's response representation. This is so that we don't have
# to rewrite any of the request handlers whenever we change frameworks
HTTP_Response	= namedtuple('HTTP_Response',	('code', 'headers', 'body'))

## Named tuple used to describe a request url
HTTP_URL	= namedtuple('HTTP_URL',	('scheme', 'host', 'path', 'query'))

## Named tuple used to describe a request
HTTP_Request	= namedtuple('HTTP_Request', 	('version', 'method', 'headers', 'url','body', 'parent_object'))

## Convert a request from the representation of aiohttp to a HTTP_Request
# @param request	Request to convert
# @param rwrite		Callable which rewrites the path. Can be used to get
#			A minfo part, or strip of certain characters, etc
def convert(request, rwrite = lambda r:r.path):
	# convert the aiohttp request object to a HTTP_Request tuple
	# so that it can be processed by the HTTP_Presentation class
	return HTTP_Request(
		version = request.version,
		method = request.method,
		headers = request.headers,
		url = HTTP_URL(
			scheme	= request.scheme,
			host	= request.host,
			# url relative to the presentation directory
			path	= rwrite(request),
			query	= request.query,
		),
		body = request.read(),
		parent_object = request
	)

## transform a standard HTTP_Response named tuple to a form the webserver understands
def export(response):
	return web.Response(
		status  = response.code,
		headers = response.headers,
		body    = response.body,
	)

## Check whether the client has the resource cached, and send the appropriate headers
# @param self		Object pointer
# @param request	The request currently being processed
# @param filename	Source file of the request
# @param do_cache	Whether to enable caching or not
# @param mtime		Use this mtime instead of stat-ing it yourself
#
# @return		Boolean if the the client has the resource cached,
#			so that the calling function knows what to do further
def client_has_cached(filename, request, do_cache = True, mtime = None):

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
	
	tstamp = mtime or os.path.getmtime(filename)
	
	lm = datetime.utcfromtimestamp(tstamp).replace(tzinfo=pytz.utc, microsecond = 0)
	
	if do_cache and imsp == lm:
	
		return HTTP_Response(
			code = 304, 
			headers = {
				"Cache-Control":"must-revalidate"
				} if do_cache else {},
			body = ""
			)
	else:			
		return HTTP_Response(
			code = 200, 
			headers = {
				"Cache-Control":"must-revalidate",
				"Last-Modified": lm.strftime('%a, %d %b %Y %H:%M:%S GMT')
				} if do_cache else {},
			body = ""
			)

## Log a request to stdout
# @param self		Object pointer
# @param request	Request object of the framework
# @param response	HTTP_Response named tuple
def log_request(request, response):

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
		'{}//{}{}{}'.format(
			*request.url[:2],
			request.parent_object.path,
			build_query_string(request.url.query))
		)
	)

## HTTP_Request translator system for the aiohttp framework
# @param rewrite	Callable used to rewrite the path
# @param logger		Function to log the request. It must have the
#			<request>, <response> signature, and it can expect to
#			receive a HTTP_Request and HTTP_Response named tuples
def aio_translate(rewrite = lambda r:r.path, logger = lambda r,R:True):
	
	## translator initialisation function
	# @param func	Function to be decorated
	def boot(func):
		
		## Translating decorating function
		#
		# The function assumes that the last argument is the request
		# object. This way, it can be used with functions and
		# class methods
		def decorator(*args, **kwargs):
			args = list(args)
			args[-1] = convert(args[-1], rewrite)
			
			response = func(*args, **kwargs)
			
			logger(args[-1], response)
			
			return export(response)
		
		return decorator
	return boot

## Initialise static routes
# @param app	Web application to attach to
# @param pconf	Presentation configuration
# @param sconf	Server configuration
def init_static(app, pconf, sconf):

	dirname = os.path.split(__file__)[0]

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

## Wrapper function to start up all default functionality
# @param app	Web application to attach to
# @param pconf	Presentation configuration
# @param sconf	Server configuration
# @param mconf	Multiplexing configuration
def startup_defaults(app, pconf, sconf, mconf):
	multiplex.start_socket_io(app, mconf)
	init_static(app, pconf, sconf)

## Named tuple which can be used to represent a basicauth header
basicauth = namedtuple('basicauth', ['uname', 'passwd'])

## Decode a suspected Basic Auth header
# @param header	The header text
# @param fail	Value returned on failure
def decode_basic_auth(header, fail = basicauth(None, None)):
	
	if not header:
		return fail
	
	auth = header.split(' ')
	
	if len(auth) != 2 or auth[0] != 'Basic':
		return fail
		
	try:
		astr = base64.b64decode(auth[1]).decode().split(':', 1)
	except Exception as f:
		print("Malformed Authentication header")
		print(f)
		return fail
	
	if len(astr) != 2:
		return fail
	
	return basicauth(uname = astr[0], passwd = astr[1])

