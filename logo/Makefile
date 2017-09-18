# This file is part of the WaterSlide presentation program
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

.PHONY: clean

default: all
all: plain.svg logo.png

plain.svg: logo.svg
	inkscape --file=$^ --export-plain-svg=$@

logo.png: logo.svg
	inkscape --file=$^ --export-png=$@

clean:
	rm -rf $(wildcard plain.svg logo.png favicon.ico)
