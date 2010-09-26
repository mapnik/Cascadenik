""" cascadnik - cascading sheets of style for mapnik

http://mike.teczno.com/notes/cascadenik.html

http://code.google.com/p/mapnik-utils/wiki/Cascadenik

"""

import style
# compile module
import compile as _compile
# compile function
from compile import compile
from style import stylesheet_declarations

# define Cascadenik version
VERSION = '0.2.0'

__all__ = ['compile','_compile','style','stylesheet_declarations']

def load_map(map, input, target_dir=None):
    """
    """
    compile(input, target_dir=target_dir).to_mapnik(map, target_dir)
