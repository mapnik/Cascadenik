#!/usr/bin/env python
 
import sys
import optparse
import cascadenik

def main(file, **kwargs):
    """ Given an input layers file and a directory, print the compiled
        XML file to stdout and save any encountered external image files
        to the named directory.
    """
    compiled = cascadenik.compile(file, **kwargs)
    if kwargs.get('compiled'):
        open(kwargs['compiled'],'wb').write(compiled)
    else:
        print compiled
    return 0

parser = optparse.OptionParser(usage="""%prog [options] <mml> <xml>""", version='%prog ' + cascadenik.VERSION)

parser.add_option('-d', '--dir', dest='target_dir',
                  default=None,
                  help='Write file-based resources (symbols, shapefiles, etc) to this target directory (default: temp directory is used)')

parser.add_option('--srs', dest='srs',
                  default=None,
                  help='Target srs for the compiled stylesheet. If provided, overrides default map srs in the mml (default: None)')

parser.add_option('--move', dest='move_local_files',
                  default=False,
                  help='Move local files to target --dir location in addition to remote resources (default: False)',
                  action='store_true')

parser.add_option('--no-cache', dest='no_cache',
                  default=False,
                  help='Do not cache remote files (caching on by default, e.g. no_cache=True)',
                  action='store_true')

parser.add_option('-p', '--pretty', dest='pretty',
                  default=True,
                  help='Pretty print the xml output (default: True)',
                  action='store_true')

parser.add_option('--safe-urls', dest='safe_urls',
                  default=False,
                  help='Base64 encode all urls when saved as filesystem paths (default: False)',
                  action='store_true')

parser.add_option('-v' , '--verbose', dest='verbose',
                  default=False,
                  help='Make a bunch of noise (default: False)',
                  action='store_true')

parser.add_option('--mapnik-version',dest='mapnik_version_string',
                  default=None,
                  help='The Mapnik version to target (default is 0.7.1 if not able to be autodetected)')

                  
if __name__ == '__main__':
    (options, args) = parser.parse_args()
    if not args:
        parser.error('Please specify a .mml file')
    layersfile = args[0]
    if layersfile.endswith('.mss'):
        parser.error('Only accepts an .mml file')
    if len(args) == 2:
        options.compiled = args[1]
        if not options.compiled.endswith('xml'):
           parser.error('Stylesheet Output "%s" must end with an ".xml" extension' % options.compiled)
    if options.mapnik_version_string:
        n = options.mapnik_version_string.split('.')
        if not len(n) == 3:
           parser.error('--mapnik-release is invalid, please provide major.minor.point format (e.g. 0.7.1)')
        options.mapnik_version = (int(n[0]) * 100000) + (int(n[1]) * 100) + (int(n[2]));
    sys.exit(main(layersfile, **options.__dict__))
