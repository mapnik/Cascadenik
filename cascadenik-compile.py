#!/usr/bin/env python
 
import sys
import optparse
import cascadenik

def main(file, dir, move_local_files):
    """ Given an input layers file and a directory, print the compiled
        XML file to stdout and save any encountered external image files
        to the named directory.
    """
    print cascadenik.compile(file, dir=dir, move_local_files=False)
    return 0

parser = optparse.OptionParser(usage="""cascadenik-compile.py [options] <style file>""")

parser.add_option('-d', '--dir', dest='directory',
                  help='Write to output directory')

parser.add_option('-m', '--move', dest='move_local_files',
                  help='Move local files to --dir location in addition to remote resources')
                  
if __name__ == '__main__':
    (options, args) = parser.parse_args()
    if not args:
        parser.error('Please specify a .mml file')
    layersfile = args[0]
    if layersfile.endswith('.mss'):
        parser.error('Only accepts an .mml file')
    sys.exit(main(layersfile, options.directory, options.move_local_files))
