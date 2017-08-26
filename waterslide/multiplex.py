from passlib import hash
import os
import socketio
import random, string
import netifaces
import collections
import time

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

## Class used to configure multiplexing. Behaves largely as a named tuple,
# but it handles defaults
class MConf:
	
	deflen = 16
	
	def __init__(self, rlen = 16, htype = hash.bcrypt):
		self._rlen  = rlen
		self._htype = htype
	
	@property
	def rlen(self):
		return self._rlen
	
	@property
	def htype(self):
		return self._htype

## Start the socket io subsystem
# @param app	aiohttp web app instance
# @param mconf	Instance of the Mconf library, to configure the multiplexing
def start_socket_io(app, mconf):

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

		print(t, sid, data['state'])
		
		# protect the secret
		data['secret'] = None
	
		# Avoid feedback loops by skipping the sending sid
		await sio.emit(data['socketId'], data=data, skip_sid=sid)
	

## wrapper function to get a string of random characters
# @param N	Amount of characters to return
# @return	'N' random characters
def getrandom(N=MConf.deflen):
	return ''.join(random.SystemRandom().choice(string.ascii_lowercase + string.ascii_uppercase + string.digits) for _ in range(N))

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

## Create a multiplex configuration dictionary based upon the passed settings
# @param mconf		Multiplexing configuration
# @return		A dictionary based upon the configuration in mconf
def create_multiplex_dict(mconf):
	
	secret = getrandom(mconf.rlen)

	socket_id = mconf.htype.encrypt(secret)
	
	return	{
		'secret':secret,
		'id': socket_id,
		'url':'http://{}:9090'.format(get_ip_addr())
		}

## @}
