
// Configuration parameters for the multiplex event handlers and intialisation code
var multiplex = {
	debug: false, // Current debugging status
	
	init_dbg_state: true, //Whether to output debug information during intialisation
	post_init_dbg_state: false, // Wheter to output debug information after initialisation
	
	
	// Whether to be fully compliant with the implementation found in the Reveal.js
	// repository. Being compliant currently only entails not sending the client_id
	// along with a broadcast. The client_id is one of the tools used to prevent
	be_compliant: false,
	
	range: 1024, // had to pick something
	};

function dbg(args) {
	if (multiplex.debug != true)
		return;
	
	console.log.apply(this, arguments);
}

(function() {
	
	multiplex.debug = multiplex.init_dbg_state;
	
	var Semaphore = {};
	var client_id = Math.floor(Math.random() * multiplex.range);

	var mult_conf = Reveal.getConfig().multiplex;

	if (!(mult_conf.id && mult_conf.url)) {
		dbg(Date.now(), "No multiplexing configuration available");
		return;
	}
	
	var socket = io.connect(multiplex.url);
	
	socket.on(mult_conf.id, get);
	dbg(Date.now(), "Registered as a Client");
	
	// Don't emit events from inside of notes windows
	// also only register as a master when we think we have a secret
	if (mult_conf.secret && !window.location.search.match('/receiver/gi')) {

		// Monitor events that trigger a change in state
		Reveal.addEventListener('slidechanged', post);
		Reveal.addEventListener('fragmentshown', post);
		Reveal.addEventListener('fragmenthidden', post);
		Reveal.addEventListener('overviewhidden', post);
		Reveal.addEventListener('overviewshown', post);
		Reveal.addEventListener('paused', post);
		Reveal.addEventListener('resumed', post);
		
		dbg(Date.now(), "Registered as a Master")
		
	}
	
	multiplex.debug = multiplex.post_init_dbg_state;

	/**
	 * Socket.io message handler
	 * @param data	Data received from the multiplex server
	 *
	 * This function stores the received state in the Semaphore, so that
	 * when the post() method triggers because Reveal.js changes the state
	 * it got from this function, it knows which one not to rebroadcast
	 * back to the network. This is one of the tools used to prevent
	 * feedback loops on the network.
	 */
	function get(data) {
		// ignore data from sockets that aren't ours
		// Also ignore data when we got back an event we just
		// broadcast (to prevent feedback loops)
		if (	data.socketId !== mult_conf.id || 
			window.location.host === 'localhost:1947' ||
			data.client_id == client_id
		)
			return;
		
		// Set the semaphore, so we can ensure we don't send the new state back
		Semaphore = data.state;
		
		Reveal.setState(data.state);
		
		dbg(Date.now(), "rx", data.client_id, data.state);
	}
	
	/*
	 * Reveal.js state change handler for multiplexing
	 *
	 * This function sends a broadcast onto the multiplexing network
	 * whenever the presentation changes state. Before broadcasting, it
	 * checks whether or not the change is due to a change of state in
	 * another master presentation (which we received previously in the
	 * get function). When that happens, it ignores the state change, and
	 * doesn't send it onto the network, as to prevent feedback loops
	 */
	function post() {

		S = Semaphore
		s = Reveal.getState()
		
		// FIXME: The setState and getState don't return a directly
		// comparable object, so compare the lowest common denominator;
		// the elements of the getState call. This could be fixed
		// in Reveal.js itself
		if (	s.indexh == S.indexh && 
			s.indexv == S.indexv &&
			s.overview == S.overview &&
			s.paused == S.paused
		
		) {
			// clear the semaphore after ignoring an event, as
			// not to prevent events which are perfectly valid
			// and originate from this presenation itself to
			// be broadcasted
			Semaphore = {};
			return;
		} else {
		
			var messageData = {
				state: s,
				secret: mult_conf.secret,
				socketId: mult_conf.id
			};
			
			// only store the client id when we don't require strict
			// compliance with the reference implementation
			if (multiplex.be_compliant != true) {
				messageData['client_id'] = client_id
			}
			
			// check if we attempt to send the new state back
			dbg(Date.now(), "tx", client_id, s)
				
			socket.emit('multiplex-statechanged', messageData );
		}
	};
}());

/// @}
