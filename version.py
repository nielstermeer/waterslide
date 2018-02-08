# (C) 2017 Niels ter Meer
# This file is part of the WaterSlide presentation program
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Generate data.json for versioning information.
#
# This application is used to only extract versioning information using the
# code waterslide already has. Invoking the main wslide program is only
# possible when the virtual enviroment is active, which should not be
# required when one only needs the version of the program to perform
# other functions such as building a docker image.

from waterslide import version

with open('data.json', 'w') as f:
	# skip reading the data file, since we're generating it
	f.write(version.generate_data_file(True))
