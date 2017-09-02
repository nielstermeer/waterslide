import time
import sass
from waterslide import presentation, cache, httputils
from aiohttp import web
import collections
import os

##
#  @defgroup manager Presentation manager module
# 
#  @addtogroup manager
#  @{
#

## dummy class for when a presentation does not exist
class notfound():
	
	def __init__(self, path):
		self.path = path
	
	@property
	def isreal(self):
		return os.path.isdir(self.path)
	
	def handle(self, request):
		return httputils.HTTP_Response(
			code = 404,
			headers = {},
			body = 'Resource not found'
			)

## Class used to serve dynamic content
class dynamic():
	def __init__(self, path):
		
		self.path = path
		
		if not self.exists:
			return
		
		self.mtime = os.path.get(path)
		self.sass = sass.compile(fname=path)
	
	@property
	def exists(self):
		return os.path.exists(self.path)	
	
	def handle(self, request):
		
		c = httputils.client_has_cached(self.path, request)
		
		if c.code == 304:
			return c
		
		return httputils.HTTP_Response(
			code = c.code,
			headers = c.headers,
			body = self.sass
			)

class Manager():
	
	def __init__(
		self,
		docroot,
		cachesize = 32,
		pconf	= None,
	):
		self.docroot	= docroot
		self.cachesize	= cachesize
		self.pconf	= pconf if pconf else presentation.PConf()
		
		# initialise the cache depths, because we cannot do that on
		# decoration time, since 'self' isn't yet defined
		self.find.conf(depth = cachesize)
		self.get_dyn_ctnt.conf(depth = cachesize)

	## Register routes for the manager
	# @param self	Object pointer
	# @param app	app to attach to
	def register(self, app):
		app.router.add_route('GET', '/{pres:.*}/', self.handle_pres)
		app.router.add_route('GET', '/{tail:(.scss|.sass)}', self.handle_dynamic)
		app.router.add_static('/', self.docroot)
		
		return self
	
	## Get a presentation to use to serve a request
	# @param self	Object pointer
	# @param pname	Path name to the presentation requested
	@cache.cache(valid = lambda k,v: v.isreal)
	def find(self, pname):
		ppath = os.path.join(self.docroot, pname)		
		p = presentation.managed_pres(ppath, self.pconf)
		
		if p.isreal:
			return p
		else:
			return notfound(ppath)
	
	## Handle a request for a presentation
	# @param self		Object pointer
	# @param request	Request to be handled
	@httputils.aio_translate(rewrite = lambda r:r.path[1:],
					logger = httputils.log_request)
	def handle_pres(self, request):
		return self.find(request.url.path).handle(request)
	
	## Get the object to be used to serve a dynamic file request
	# @param self	Object pointer
	# @param path	Path to the file, relative to the document root
	@cache.cache(valid = lambda k,v: v.exists and v.mtime == os.path.getmtime(v.path))
	def get_dyn_ctnt(self, path):
		
		ppath = os.path.join(self.docroot, pname)
		
		d = dynamic(ppath)
		
		if d.exists:
			return d
		else:
			return notfound(ppath)
	
	## Handle a dynamic content request
	# @copydetails handle_pres
	@httputils.aio_translate(rewrite = lambda r:r.path[1:],
					logger = httputils.log_request)
	def handle_dynamic(self, request):
		return self.get_dyn_ctnt(request.url.path).handle(request)

## Subcommand handling function for the manage subcommand
def serve(argn, argv):

	docroot = './'
	# continue parsing
	i = argn
	while i < len(argv):
		
		if argv[i] in ('--nop'):
			pass
		else:
			docroot = argv[i]
		i += 1
	
	man = Manager(docroot)
	
	app = web.Application()
	
	man.register(app)
	
	web.run_app(app, host='0.0.0.0', port=9090)

## @}
