default: wheel

.PHONY: docs clean

docs: $(wildcard **.py)
	doxygen Doxyfile; make -C latex

build:
	python3 setup.py build

wheel:
	python3 setup.py bdist_wheel

clean:
	rm -rf $(wildcard html latex build dist waterslide.egg-info)
