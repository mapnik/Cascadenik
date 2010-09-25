#!/usr/bin/env python

import os
import sys
import optparse
import cascadenik
import tempfile
import mapnik2 as mapnik

try:
    import xml.etree.ElementTree as ElementTree
    from xml.etree.ElementTree import Element
except ImportError:
    try:
        import lxml.etree as ElementTree
        from lxml.etree import Element
    except ImportError:
        import elementtree.ElementTree as ElementTree
        from elementtree.ElementTree import Element

def main(file, **kwargs):
    """ Given an input layers file and a directory, print the compiled
        XML file to stdout and save any encountered external image files
        to the named directory.
    """
    mmap = mapnik.Map(1, 1)
    # allow [zoom] filters to work
    mmap.srs = '+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null'
    load_kwargs = dict([(k, v) for (k, v) in kwargs.items() if k in ('target_dir', 'move_local_files')])
    cascadenik.load_map(mmap, file, **load_kwargs)
    
    (handle, filename) = tempfile.mkstemp(suffix='.xml', prefix='cascadenik-mapnik-')
    os.close(handle)
    mapnik.save_map(mmap, filename)
    
    if kwargs.get('pretty'):
        doc = ElementTree.fromstring(open(filename, 'rb').read())
        print doc
        cascadenik._compile.indent(doc)
        f = open(filename, 'wb')
        doc.write(f)
        f.close()
        
    if kwargs.get('compiled'):
        os.rename(filename, kwargs['compiled'])
    else:
        print open(filename, 'r').read()
        os.unlink(filename)
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
                  help='The Mapnik version to target (default is 0.8.0 if not able to be autodetected)')

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
