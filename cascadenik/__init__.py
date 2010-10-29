""" cascadnik - cascading sheets of style for mapnik

http://mike.teczno.com/notes/cascadenik.html

http://code.google.com/p/mapnik-utils/wiki/Cascadenik

"""
from os import mkdir, chmod
from os.path import isdir, realpath, expanduser, dirname, exists
from urlparse import urlparse

import style
# compile module
import compile as _compile
# compile function
from compile import compile, Directories
from style import stylesheet_declarations

# define Cascadenik version
VERSION = '1.0.0'
CACHE_DIR = '~/.cascadenik'

__all__ = ['load_map', 'compile','_compile','style','stylesheet_declarations']

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
