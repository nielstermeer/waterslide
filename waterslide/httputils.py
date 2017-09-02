from datetime import datetime
import pytz
import os
from aiohttp import web
from email import utils
from collections import namedtuple

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
# @return		Boolean if the the client has the resource cached,
#			so that the calling function knows what to do further
def client_has_cached(filename, request, do_cache = True):

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