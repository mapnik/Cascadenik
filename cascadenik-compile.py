#!/usr/bin/env python

import os
import sys
import optparse
import cascadenik
import tempfile
import mapnik

from os.path import realpath, dirname

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

def main(src_file, dest_file, **kwargs):
    """ Given an input layers file and a directory, print the compiled
        XML file to stdout and save any encountered external image files
        to the named directory.
    """
    mmap = mapnik.Map(1, 1)
    # allow [zoom] filters to work
    mmap.srs = '+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null'
    load_kwargs = dict([(k, v) for (k, v) in kwargs.items() if k in ('verbose', 'datasources_local_cfg')])
    cascadenik.load_map(mmap, src_file, target_dir=dirname(realpath(dest_file)), **load_kwargs)
    
    (handle, tmp_file) = tempfile.mkstemp(suffix='.xml', prefix='cascadenik-mapnik-')
    os.close(handle)
    mapnik.save_map(mmap, tmp_file)
    
    if kwargs.get('pretty'):
        doc = ElementTree.fromstring(open(tmp_file, 'rb').read())
        cascadenik._compile.indent(doc)
        f = open(tmp_file, 'wb')
        ElementTree.ElementTree(doc).write(f)
        f.close()
        
    os.rename(tmp_file, dest_file)
    return 0

parser = optparse.OptionParser(usage="""%prog [options] <mml> <xml>""", version='%prog ' + cascadenik.VERSION)

parser.set_defaults(no_cache=False, pretty=True, safe_urls=False, verbose=False, datasources_local_cfg=None)

#parser.add_option('-d', '--dir', dest='target_dir',
#                  help='Write file-based resources (symbols, shapefiles, etc) to this target directory (default: current working directory is used)')

parser.add_option('--srs', dest='srs',
                  help='Target srs for the compiled stylesheet. If provided, overrides default map srs in the mml (default: None)')

parser.add_option('--no-cache', dest='no_cache',
                  help='Do not cache remote files (caching on by default, e.g. no_cache=True)',
                  action='store_true')

parser.add_option('-p', '--pretty', dest='pretty',
                  help='Pretty print the xml output (default: True)',
                  action='store_true')

parser.add_option('--safe-urls', dest='safe_urls',
                  help='Base64 encode all urls when saved as filesystem paths (default: False)',
                  action='store_true')

parser.add_option('-v' , '--verbose', dest='verbose',
                  help='Make a bunch of noise (default: False)',
                  action='store_true')

parser.add_option('--mapnik-version',dest='mapnik_version_string',
                  help='The Mapnik version to target (default is 0.7.1 if not able to be autodetected)')

parser.add_option('-l' , '--locals', dest='datasources_local_cfg',
                  help='Use the specified .cfg file to provide local overrides to datasources and variables',
                  type="string")


if __name__ == '__main__':
    (options, args) = parser.parse_args()
    
    if not args:
        parser.error('Please specify .mml and .xml files')

    layersfile, outputfile = args[0:2]
    
    print >> sys.stderr, 'output file:', outputfile, dirname(realpath(outputfile))

    if not layersfile.endswith('.mml'):
        parser.error('Input must be an .mml file')

    if not outputfile.endswith('.xml'):
        parser.error('Output must be an .xml file')

    if options.mapnik_version_string:
        n = options.mapnik_version_string.split('.')
        if not len(n) == 3:
           parser.error('--mapnik-release is invalid, please provide major.minor.point format (e.g. 0.7.1)')
        options.mapnik_version = (int(n[0]) * 100000) + (int(n[1]) * 100) + (int(n[2]));

    sys.exit(main(layersfile, outputfile, **options.__dict__))
