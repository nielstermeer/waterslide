# This file is part of the WaterSlide presentation program
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

default: wheel

.PHONY: docs clean

docs: $(wildcard **.py)
	( cat Doxyfile ; echo "PROJECT_NUMBER="`./wslide version --release`) | doxygen - && make -C latex

build:
	python3 setup.py build

wheel:
	python3 setup.py bdist_wheel

clean:
	rm -rf $(wildcard html latex build dist waterslide.egg-info)
