all: cssutils
	#

cssutils:
	curl -sO "http://pypi.python.org/packages/source/c/cssutils/cssutils-0.9.5.1.zip"
	unzip -q cssutils-0.9.5.1.zip
	mv cssutils-0.9.5.1/src/cssutils ./
	mv cssutils-0.9.5.1/src/encutils ./cssutils/
	rm -rf cssutils-0.9.5.1 cssutils-0.9.5.1.zip

clean:
	rm -rf cssutils
