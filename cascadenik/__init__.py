""" cascadnik - cascading sheets of style for mapnik

http://mike.teczno.com/notes/cascadenik.html

http://code.google.com/p/mapnik-utils/wiki/Cascadenik

"""
from os import mkdir, chmod
from os.path import isdir, realpath, expanduser

import style
# compile module
import compile as _compile
# compile function
from compile import compile, Directories
from style import stylesheet_declarations

# define Cascadenik version
VERSION = '0.2.0'
CACHE_DIR = '~/.cascadenik'

__all__ = ['load_map', 'compile','_compile','style','stylesheet_declarations']

def load_map(map, input, target_dir, cache_dir=None, datasources_cfg=None, verbose=False):
    """
    """
    if cache_dir is None:
        cache_dir = expanduser(CACHE_DIR)
        
        # only make the cache dir if it wasn't user-provided
        if not isdir(cache_dir):
            mkdir(cache_dir)
            chmod(cache_dir, 0755)

    dirs = Directories(target_dir, realpath(cache_dir))
    compile(input, dirs, datasources_cfg=datasources_cfg, verbose=verbose).to_mapnik(map, dirs)
