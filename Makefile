VERSION:=$(shell cat VERSION.txt)
TARBALL=cascadenik-$(VERSION).tar.gz

all: dist/$(TARBALL)

dist/$(TARBALL):
	python setup.py sdist build
	rm -rf *.egg* *.pyc build

clean:
	rm -rf *.egg* *.pyc build dist
