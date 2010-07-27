""" cascadnik - cascading sheets of style for mapnik

http://mike.teczno.com/notes/cascadenik.html

http://code.google.com/p/mapnik-utils/wiki/Cascadenik

"""

import os, tempfile
import style
# compile module
import compile as _compile
# compile function
from compile import compile
from style import stylesheet_rulesets, rulesets_declarations, stylesheet_declarations

# define Cascadenik version
VERSION = '0.2.0'

__all__ = ['compile','_compile','style','stylesheet_rulesets', 'rulesets_declarations', 'stylesheet_declarations']

def load_map(map, input,**kwargs):
    """
    """
#    try:
#        import mapnik2 as mapnik
#    except ImportError:
    try:
        import mapnik
    except ImportError:
        # it's not going to be possible to use load_map(), but nothing else requires mapnik
        pass
    
    (handle, compiled) = tempfile.mkstemp('.xml', 'cascadenik-compiled-')
    os.close(handle)
    
    open(compiled, 'w').write(compile(input,**kwargs))
    return mapnik.load_map(map, compiled)
