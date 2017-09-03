from sys import argv
import os
import socketio
import random, string
import netifaces
import collections
import time
import hashlib
from waterslide.httputils import HTTP_Response

##
#  @defgroup multiplex Presentation multiplexing module
# 
# The multiplexing module controls the multiplexing of presenatations
# across different browser windows and hosts.
#
# In contrast with Reveal's reference implementation, this implementation is
# robust against multiple masters on the network. In the end, this boiled down
# to programming the broadcasting parts NOT to rebroadcast the events they
# received. Without this feature, if circumstances were just "right", the whole
# network would spaz out, the presentations would constantly switch slides in
# a feedback loop, and the only way to resolve it was to kill the server.
#
# For the javascript event handlers, this meant blocking the
# stateChanged() event handlers from rebroadcasting the received event, and
# on the server side this meant skipping the connection from which the event
# was received while emit()-ing.
#
# On top of that, to keep the javascript plugin largely compatible with the
# reference multiplex server, but also being able to ignore the rebroadcasts
# from it (it doesn't skip the event origin, in contrast with this
# implementation), we add a 'client_id' field to the broadcast.
# since the server broadcasts the events to all connected clients, we know
# which broadcasts to ignore. The client_id is randomly selected from a range
# of 0:1024 (by default) for each browser window, and remains the same for
# the duration of that window's session. 
#
#  @addtogroup multiplex
#  @{

## Get the ip address of the host
# @return Ip address of the host
def get_ip_addr():
	
	ips = []
		
	ifaces = netifaces.interfaces() 
	
	for ifc in ifaces:
	
		if_addrs = netifaces.ifaddresses(ifc).get(netifaces.AF_INET)
		
		for if_addr in if_addrs or []:
			ips.append(if_addr.get('addr'))

		for i in ips:

			if not i.startswith('127.'):
				return i
	
	return '127.0.0.1'

## Wrapper to standarise multiplex secrets and socketId's. Wraps sha512.
#
# This kind of wrapper is useful for when other hashes are an option, since
# these wrappers provide a standarised interface.
class mh_sha512:
	def encrypt(plain):
		return hashlib.sha512(bytes(plain, 'utf-8')).hexdigest()
	
	def verify(plain, digest):
		return digest == mh_sha512.encrypt(plain)

algs_avail = {
"sha512": mh_sha512,
}
## Class used to configure multiplexing. Behaves largely as a named tuple,
# but it handles defaults
class MConf:
	
	deflen = 16
	
	do_multiplex = False
	just_serve = False
	
	MX_server = 'http://' + get_ip_addr() + ':9090'
	rlen = 16
	htype = mh_sha512
	
	autoslave = False

	@property
	def startserver(self):
		return self.do_multiplex or self.just_serve
	
	helptext = '''
-m, --multiplex         Enable multiplexing of presentations. This enables a
                        Socket.io server, and adds the configuration to the
                        presenations. Pass the "master" query in the url to
                        obtain control of the presenation
                        (e.g.: localhost/?master)
--multiplex-length	Amount of random characters to request for
                        the hash input
-X, --multiplex-server  Server to point the multiplex url to. Will default to
                        the local machine's ip address and port number if not
                        configured
--just-serve            Startup the multiplex server, but do not configure the
                        presentations to multiplex. This is useful for server
                        deployments, where the server (besides serving
                        presentations) also functions as a remote multiplexing
                        server.

--autoslave             Autoslave any client which isn't a master. Is the
                        default for the serve subcommand
--no-autoslave          Disable autoslaving. Is the default for the
                        manage subcommand

-A, --mh_algorithm      Configure the hashing algorithm used to transform the
                        automatically generated secret to a socket ID.
                        Currently, only "bcrypt" is available, but this option
                        is provided for forwards compatability
'''
	def parse(self, argn):
		
		if argv[argn] in ("-m", "--multiplex"):
			self.do_multiplex = True
			ret = 1
		elif argv[argn] == "--multiplex-length":
			self._rlen = argv[argn+1]
			ret = 2
		elif argv[argn] in ('-A','--mh_algorithm') \
		 and argv[argn] in algs_avail.keys():
		 
			self.htype = algs_avail[argv[argn]]
			ret = 2
		elif argv[argn] in ("-X", "--multiplex-server"):
			
			temp = argv[argn+1]
			
			if not temp.startswith('http'):
				temp = 'http://' + temp
			
			self.MX_server = temp
			ret = 2
		elif argv[argn] in ("--just-serve",):
			self.just_serve = True
			return 1
		elif argv[argn] == "--autoslave":
			self.autoslave = True
			ret = 1
		elif argv[argn] == "--no-autoslave":
			self.autoslave = False
			ret = 1
		else:
			return 0
		return ret

## Start the socket io subsystem
# @param app	aiohttp web app instance
# @param mconf	Instance of the Mconf library, to configure the multiplexing
def start_socket_io(app, mconf):

	if not mconf.startserver:
		return

	print("Starting up SocketIO endpoint")
	sio = socketio.AsyncServer()
	sio.attach(app)

	@sio.on('multiplex-statechanged')
	async def fwd_socketio_msg(sid, data):

		t = time.time()

		# check if the secret is actually present, and matches
		# up with the socket ID. If so, we have an authorised master,
		# and we can continue processing.
		if data.get('secret') in ('undefined', None, '') or \
		not mconf.htype.verify(data['secret'], data.get('socketId')):
			print(t, "refused to forward for", sid)
			return

		print(t, data['socketId'][:10], data['state'])
		
		# protect the secret
		data['secret'] = None
	
		# Avoid feedback loops by skipping the sending sid
		await sio.emit(data['socketId'], data=data, skip_sid=sid)
	

## wrapper function to get a string of random characters
# @param N	Amount of characters to return
# @return	'N' random characters
def getrandom(N=MConf.deflen):
	return ''.join(random.SystemRandom().choice(string.ascii_lowercase + string.ascii_uppercase + string.digits) for _ in range(N))

## Create a multiplex configuration dictionary based upon the passed settings
# @param mconf		Multiplexing configuration
# @return		A dictionary based upon the configuration in mconf
def create_multiplex_dict(mconf):
	
	secret = getrandom(mconf.rlen)

	socket_id = mconf.htype.encrypt(secret)
	
	return	{
		'secret':secret,
		'id': socket_id,
		'url': mconf.MX_server
		}
	
## @}
