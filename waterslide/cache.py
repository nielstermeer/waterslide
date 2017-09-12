# (C) 2017 Niels ter Meer
# This file is part of the WaterSlide presentation program
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import collections

##
#  @defgroup cache Caching module
# 
#  @addtogroup cache
#  @{
#

CStats = collections.namedtuple('CStats', ['hits', 'misses', 'csize'])

## Class used to maintain state in the caching decorator
#
# Since variables in the parent's scope are read only in the functions it
# encloses, we cannot use these variables directly in the parent's scope.
# Instead we put all the caching state in this class, wherein we can modify
# the variables without problems
class cache_state():
	## Cache hits
	hits = 0
	## Cache misses
	misses = 0
	## Maximum cache size
	depth = 32
	## The cache itself
	cache = collections.OrderedDict()
	## Callable used to determine if the cached object is still valid.
	# It defaults to true
	valid = lambda k,v: True

## Caching decorator initialisation function
# @param depth		Cache depth
# @param valid		Callable used to determine if the cached object is still valid
def cache(depth = 32, valid = lambda k,v: True):
	
	## Helper function to bring the object cached by key to the top of
	# the cache
	def touch(cache, key):
		val = cache.get(key)
		del cache[key]
		cache[key] = val
	
	## Caching initialisation function
	# @param func	Function to cache the output from
	def boot(func):
		state = cache_state()
		state.depth = depth
		state.valid = valid

		## Get the cache's current status
		def status():
			return CStats(state.hits, state.misses, len(state.cache))

		## Purge the cache, reset stats to zero
		# @copydetails conf
		def purge(depth = None, valid = None):			
			state.cache = collections.OrderedDict()
			state.misses = 0
			state.hits = 0
			conf(depth, stale)

		## Configure cache after initialisation
		# @param depth	New cache depth. If not set, keep the old setting
		# @param valid	Checking callable. If not set, keep the old callable
		def conf(depth = None, valid = None):
			if depth:
				state.depth = depth
			if valid:
				state.valid = valid

		## Actual caching function decorator
		#
		# The decorator assumes that the last argument is the key to be
		# used. This is also why this decorator works for class methods
		# and functions
		def decorator(*args, **kwargs):

			ret = None
			key = args[-1]
			
			
			if key in state.cache and state.valid(key, state.cache[key]):
				touch(state.cache, key)
				ret = state.cache[key]
				state.hits += 1
			else:
				ret = func(*args, **kwargs)
				state.cache[key] = ret
				state.misses += 1

			while len(state.cache) > state.depth:
				state.cache.popitem(False)

			return ret
		
		# bind function references
		decorator.status = status
		decorator.purge	 = purge
		decorator.conf   = conf
		
		return decorator
	
	return boot

## @}
