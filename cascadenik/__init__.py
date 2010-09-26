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

__all__ = ['compile','_compile','style','stylesheet_declarations']

def load_map(map, input, target_dir, cache_dir=None):
    """
    """
    if cache_dir is None:
        cache_dir = expanduser('~/.cascadenik')
        
        if not isdir(cache_dir):
            mkdir(cache_dir)
            chmod(cache_dir, 0755)

    dirs = Directories(target_dir, realpath(cache_dir))
    compile(input, dirs).to_mapnik(map, dirs)
