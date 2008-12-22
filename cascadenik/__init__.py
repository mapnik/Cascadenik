import os, tempfile
import compile, style
from compile import compile
from style import stylesheet_rulesets, rulesets_declarations, stylesheet_declarations

try:
    import mapnik
except ImportError:
    # it's not going to be possible to use load_map(), but nothing else requires mapnik
    pass

def load_map(map, input):
    """
    """
    (handle, compiled) = tempfile.mkstemp('.xml', 'cascadenik-compiled-')
    os.close(handle)

    open(compiled, 'w').write(compile(input))
    return mapnik.load_map(map, compiled)
