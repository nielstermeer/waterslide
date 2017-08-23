from passlib import hash
import socketio
import random, string
import netifaces
import collections

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
	sio = socketio.AsyncServer(logger=True)
	sio.attach(app)

	@sio.on('multiplex-statechanged')
	async def fwd_socketio_msg(sid, data):

		if data.get('secret') in ('undefined', None, ''):
			return
	
		if not mconf.htype.verify(data['secret'], data.get('socketId')):
			return
	
		# protect the secret
		data['secret'] = None
	
		#print("statechanged ", sid, data)
		await sio.emit(data['socketId'], data=data)


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
