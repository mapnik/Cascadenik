""" Cascading sheets of style for mapnik

The introductory blog post:
  http://mike.teczno.com/notes/cascadenik.html

The code:
  https://github.com/mapnik/Cascadenik
"""
__version__ = '2.6.3'

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
MAPNIK_VERSION_STR = ('%07d' % MAPNIK_VERSION)
MAPNIK_VERSION_STR = '.'.join(map(str, (int(MAPNIK_VERSION_STR[:2]), int(MAPNIK_VERSION_STR[2:-2]), int(MAPNIK_VERSION_STR[-2:]))))

from . import style
from .parse import stylesheet_declarations

# compile module -> "_compile"
from . import compile as _compile

# compile function -> "compile"
from .compile import compile, Directories

# define Cascadenik default cache directory
CACHE_DIR = '~/.cascadenik'

__all__ = ['load_map', 'compile', '_compile', 'style', 'stylesheet_declarations']

def load_map(map, src_file, output_dir, scale=1, cache_dir=None, datasources_cfg=None, user_styles=[], verbose=False):
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
        
          scale:
            Optional scale value for output map, 2 doubles the size for high-res displays.
        
          cache_dir:
            ...
        
          datasources_cfg:
            ...
        
          user_styles:
            A optional list of files or URLs, that override styles defined in
            the map source. These are evaluated in order, with declarations from
            later styles overriding those from earlier styles.
        
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
    compile(src_file, dirs, verbose, datasources_cfg=datasources_cfg, user_styles=user_styles, scale=scale).to_mapnik(map, dirs)
