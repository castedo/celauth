
all:
	@echo Nothing to do. Try one of the following:
	@echo make package
	@echo make clean
.PHONY : all

package:
	./setup.py bdist_rpm
.PHONY : package

clean:
	rm -r build/
	rm -r dist/
.PHONY : clean

