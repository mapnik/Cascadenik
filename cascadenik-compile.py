#!/usr/bin/env python

import os
import sys
import shutil
import optparse
import tempfile
from os.path import realpath, dirname

import cascadenik
from cascadenik import mapnik

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
    load_kwargs = dict([(k, v) for (k, v) in kwargs.items() if k in ('cache_dir', 'scale', 'verbose', 'datasources_cfg', 'user_styles')])
    cascadenik.load_map(mmap, src_file, dirname(realpath(dest_file)), **load_kwargs)
    
    (handle, tmp_file) = tempfile.mkstemp(suffix='.xml', prefix='cascadenik-mapnik-')
    os.close(handle)
    mapnik.save_map(mmap, tmp_file)
    
    if kwargs.get('pretty'):
        doc = ElementTree.fromstring(open(tmp_file, 'rb').read())
        cascadenik._compile.indent(doc)
        f = open(tmp_file, 'wb')
        ElementTree.ElementTree(doc).write(f)
        f.close()
        
    # manually unlinking seems to be required on windows
    if os.path.exists(dest_file):
        os.unlink(dest_file)

    os.chmod(tmp_file, 0666^os.umask(0))
    shutil.move(tmp_file, dest_file)
    return 0

parser = optparse.OptionParser(usage="""%prog [options] <mml> <xml>""", version='%prog ' + cascadenik.__version__)

parser.set_defaults(cache_dir=None, pretty=True, verbose=False, scale=1, user_styles=[], datasources_cfg=None)

# the actual default for cache_dir is handled in load_map(),
# to ensure that the mkdir behavior is correct.
parser.add_option('-c', '--cache-dir', dest='cache_dir',
                  help='Cache file-based resources (symbols, shapefiles, etc) to this directory. (default: %s)' % cascadenik.CACHE_DIR)

parser.add_option('-d' , '--datasources-config', dest='datasources_cfg',
                  help='Use the specified .cfg file to provide local overrides to datasources and variables.',
                  type="string")

parser.add_option('--srs', dest='srs',
                  help='Target srs for the compiled stylesheet. If provided, overrides default map srs in the mml. (default: None)')

parser.add_option('--2x', dest='scale', action='store_const', const=2,
                  help='Optionally scale all values (lengths and scale denominators) in output xml by two, suitable for display on high-resolution (e.g. iPhone) screens.')

parser.add_option('--style', dest='user_styles', action='append',
                  help='Look for additional styles in the named file, which will override anything provided in the MML. Any number of these can be provided.')

parser.add_option('-p', '--pretty', dest='pretty',
                  help='Pretty print the xml output. (default: True)',
                  action='store_true')

parser.add_option('-v' , '--verbose', dest='verbose',
                  help='Make a bunch of noise. (default: False)',
                  action='store_true')

if __name__ == '__main__':
    (options, args) = parser.parse_args()
    
    if not len(args) == 2:
        parser.error('Please specify .mml and .xml files')

    layersfile, outputfile = args[0:2]
    
    print >> sys.stderr, 'output file:', outputfile, dirname(realpath(outputfile))

    if not layersfile.endswith('.mml'):
        parser.error('Input must be an .mml file')

    if not outputfile.endswith('.xml'):
        parser.error('Output must be an .xml file')

    sys.exit(main(layersfile, outputfile, **options.__dict__))
