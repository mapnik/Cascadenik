import sys
import optparse
import cascadenik

def main(file, dir):
    """ Given an input layers file and a directory, print the compiled
        XML file to stdout and save any encountered external image files
        to the named directory.
    """
    print cascadenik.compile(file, dir)
    return 0

parser = optparse.OptionParser(usage="""compile.py [options] <style file>""")

parser.add_option('-d', '--dir', dest='directory',
                  help='Write to output directory')

if __name__ == '__main__':
    (options, args) = parser.parse_args()
    layersfile = args[0]
    sys.exit(main(layersfile, options.directory))
