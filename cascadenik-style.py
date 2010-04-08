#!/usr/bin/env python

import sys
import os.path
import cascadenik

# monkey with sys.path due to some weirdness inside cssutils
sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from cssutils.tokenize2 import Tokenizer as cssTokenizer

def main(filename):
    """ Given an input file containing nothing but styles, print out an
        unrolled list of declarations in cascade order.
    """
    input = open(filename, 'r').read()
    declarations = cascadenik.stylesheet_declarations(input)
    
    for dec in declarations:
        print dec.selector,
        print '{',
        print dec.property.name+':',
        
        if cascadenik.style.properties[dec.property.name] in (cascadenik.style.color, cascadenik.style.boolean, cascadenik.style.numbers):
            print str(dec.value.value)+';',
        
        elif cascadenik.style.properties[dec.property.name] is cascadenik.style.uri:
            print 'url("'+str(dec.value.value)+'");',
        
        elif cascadenik.style.properties[dec.property.name] is str:
            print '"'+str(dec.value.value)+'";',
        
        elif cascadenik.style.properties[dec.property.name] in (int, float) or type(cascadenik.style.properties[dec.property.name]) is tuple:
            print str(dec.value.value)+';',
        
        print '}'
    
    return 0

if __name__ == '__main__':
    stylefile = sys.argv[1]
    sys.exit(main(stylefile))
