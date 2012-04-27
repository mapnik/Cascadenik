from itertools import chain

from cssutils.tokenize2 import Tokenizer as cssTokenizer

#
# Dummy classes.
#

class ParseException (Exception): pass

class Dummy:
    def __str__(self):
        return str(self.__class__) \
             + '(' + ', '.join( [k+'='+repr(v) for (k, v) in self.__dict__.items()] ) + ')'
    
    def __repr__(self):
        return str(self)

class Declaration (Dummy):
    def __init__(self, selector, property, value, sort_key):
        self.selector = selector
        self.property = property
        self.value = value
        self.sort_key = sort_key

class Selector (Dummy):
    def __init__(self, *elements):
        self.elements = elements[:]

class SelectorElement (Dummy):
    def __init__(self, names=None, tests=None):
        self.names = names or []
        self.tests = tests or []

    def addName(self, name):
        self.names.append(str(name))
    
    def addTest(self, test):
        self.tests.append(test)

class SelectorAttributeTest (Dummy):
    def __init__(self, property, op, value):
        assert op in ('<', '<=', '=', '!=', '>=', '>')
        self.op = op
        self.property = str(property)
        self.value = value

class Property (Dummy):
    def __init__(self, name):
        self.name = name

class Value (Dummy):
    def __init__(self, value, important):
        self.value = value
        self.important = important

css = """

Layer
{
    line-width: 0;
}

.class[zoom>1],
#id[zoom="1"]
{
    line-width: 1;
}

Layer#id[zoom>2][zoom<=3]
{
    line-width: 2;
    line-width: 3 3;
}

* Stuff
{
    line-width: "hello";
}

"""

def post_attribute(tokens):

    test_args = [None, None, None]

    while True:
        nname, value, line, col = tokens.next()
        
        if nname == 'IDENT':
            test_args[0] = value
            
            while True:
                nname, value, line, col = tokens.next()
                
                if (nname, value) in [('CHAR', '<'), ('CHAR', '>'), ('CHAR', '!')]:
                    _nname, _value, line, col = tokens.next()
        
                    if (_nname, _value) == ('CHAR', '='):
                        test_args[1] = value + _value
                    
                    elif _nname in ('NUMBER', 'STRING'):
                        test_args[1:3] = value, _value
                    
                    else:
                        raise Exception()
                
                elif (nname, value) == ('CHAR', '='):
                    test_args[1] = value
                
                elif nname in ('NUMBER', 'STRING'):
                    test_args[2] = value
                
                elif (nname, value) == ('CHAR', ']'):
                    return SelectorAttributeTest(*test_args)
                
                else:
                    raise Exception()

    raise Exception()
    
def post_block(tokens):

    while True:
        nname, value, line, col = tokens.next()
        
        if nname == 'IDENT':
            _nname, _value, line, col = tokens.next()
            
            if (_nname, _value) == ('CHAR', ':'):
                print '    a.', value
                
                while True:
                    nname, value, line, col = tokens.next()
                    
                    if (nname, value) == ('CHAR', ';'):
                        break
                    
                    elif nname != 'S':
                        print '    b.', nname, repr(value)
                
            else:
                raise Exception()
        
        if (nname, value) == ('CHAR', '}'):
            break

def post_rule(tokens, selectors):

    element = None
    elements = []
    
    while True:
        nname, value, line, col = tokens.next()
        
        if nname == 'IDENT':
            #
            # Identifier always starts a new element.
            #
            element = SelectorElement()
            elements.append(element)
            element.addName(value)
            
        elif nname == 'HASH':
            #
            # Hash is an ID selector:
            # http://www.w3.org/TR/CSS2/selector.html#id-selectors
            #
            if not element:
                element = SelectorElement()
                elements.append(element)
        
            element.addName(value)
        
        elif (nname, value) == ('CHAR', '.'):
            while True:
                nname, value, line, col = tokens.next()
                
                if nname == 'IDENT':
                    #
                    # Identifier after a period is a class selector:
                    # http://www.w3.org/TR/CSS2/selector.html#class-html
                    #
                    if not element:
                        element = SelectorElement()
                        elements.append(element)
                
                    element.addName('.'+value)
                    break
                
                else:
                    raise ParseException('', line, col)
        
        elif (nname, value) == ('CHAR', '*'):
            #
            # Asterisk character is a universal selector:
            # http://www.w3.org/TR/CSS2/selector.html#universal-selector
            #
            if not element:
                element = SelectorElement()
                elements.append(element)
        
            element.addName(value)

        elif (nname, value) == ('CHAR', '['):
            #
            # Left-bracket is the start of an attribute selector:
            # http://www.w3.org/TR/CSS2/selector.html#attribute-selectors
            #
            test = post_attribute(tokens)
            element.addTest(test)
        
        elif (nname, value) == ('CHAR', ','):
            #
            # Comma delineates one of a group of selectors:
            # http://www.w3.org/TR/CSS2/selector.html#grouping
            #
            # Recurse here.
            #
            selectors.append(Selector(*elements))
            return post_rule(tokens, selectors)
        
        elif (nname, value) == ('CHAR', '{'):
            #
            # Left-brace is the start of a block:
            # http://www.w3.org/TR/CSS2/syndata.html#block
            #
            # Return a full block here.
            #
            selectors.append(Selector(*elements))
            post_block(tokens)
            return selectors

print css

tokens = cssTokenizer().tokenize(css)

while True:
    print '-' * 20
    print post_rule(tokens, [])
