.PHONY: docs clean

docs: $(wildcard **.py)
	doxygen Doxyfile; make -C latex

clean:
	rm -rf $(wildcard html latex)
