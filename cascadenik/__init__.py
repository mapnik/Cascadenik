""" cascadnik - cascading sheets of style for mapnik

http://mike.teczno.com/notes/cascadenik.html

http://code.google.com/p/mapnik-utils/wiki/Cascadenik

"""
from os import mkdir, chmod
from os.path import isdir, realpath, expanduser, dirname, exists
from urlparse import urlparse

# import mapnik
try:
    import mapnik
except ImportError:
    import mapnik2 as mapnik

# detect mapnik version, or assume 0.7.1 if no function exists.
MAPNIK_VERSION = hasattr(mapnik, 'mapnik_version') and mapnik.mapnik_version() or 701

# make a nice version-looking string out of it, like "0.7.1".
MAPNIK_VERSION_STR = '.'.join(map(str, map(int, (('%06d' % MAPNIK_VERSION)[o:][:2] for o in (-6, -4, -2)))))

from . import style
from .parse import stylesheet_declarations

# compile module -> "_compile"
from . import compile as _compile

# compile function -> "compile"
from .compile import compile, Directories

# define Cascadenik version
VERSION = '1.0.0'
CACHE_DIR = '~/.cascadenik'

__all__ = ['load_map', 'compile', '_compile', 'style', 'stylesheet_declarations']

def load_map(map, src_file, output_dir, cache_dir=None, datasources_cfg=None, verbose=False):
    """ Apply a stylesheet source file to a given mapnik Map instance, like mapnik.load_map().
    
        Parameters:
        
          map:
            Instance of mapnik.Map.
        
          src_file:
            Location of stylesheet .mml file. Can be relative path, absolute path,
            or fully-qualified URL of a remote stylesheet.
        
          output_dir:
            ...
        
        Keyword Parameters:
        
          cache_dir:
            ...
        
          datasources_cfg:
            ...
        
          verbose:
            ...
    """
    scheme, n, path, p, q, f = urlparse(src_file)
    
    if scheme in ('file', ''):
        assert exists(src_file), "We'd prefer an input file that exists to one that doesn't"
    
    if cache_dir is None:
        cache_dir = expanduser(CACHE_DIR)
        
        # only make the cache dir if it wasn't user-provided
        if not isdir(cache_dir):
            mkdir(cache_dir)
            chmod(cache_dir, 0755)

    dirs = Directories(output_dir, realpath(cache_dir), dirname(src_file))
    compile(src_file, dirs, verbose, datasources_cfg=datasources_cfg).to_mapnik(map, dirs)
