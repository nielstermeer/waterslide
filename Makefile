# This file is part of the WaterSlide presentation program
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

LOGO_D='logo'

default: wheel

.PHONY: docs clean logos webrsc

docs: $(wildcard **.py)
	( cat Doxyfile ; echo "PROJECT_NUMBER="`./wslide version --release`) | doxygen - && make -C latex

build: logos webrsc
	python3 setup.py build

wheel: logos webrsc
	python3 setup.py bdist_wheel

webrsc: logos waterslide/web-resources/logo.png waterslide/web-resources/logo.svg

waterslide/web-resources/logo.png: logos
	cp logo/logo.png $@

waterslide/web-resources/logo.svg: logos
	cp logo/plain.svg $@

logos:
	make -C $(LOGO_D)

clean:
	rm -rf $(wildcard html latex build dist waterslide.egg-info)
	make -C $(LOGO_D) clean
