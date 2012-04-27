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

.class[zoom > 1],
#id[zoom = "1"]
{
    line-width: 1;
}

Layer#id[zoom >2][ zoom<= 3]
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

    def next_scalar(tokens):
        while True:
            tname, tvalue, line, col = tokens.next()
            if tname == 'NUMBER':
                return tvalue
            elif tname == 'STRING':
                return tvalue[1:-1]
            elif tname != 'S':
                raise ParseException('', line, col)
    
    def finish_attribute(tokens):
        while True:
            tname, tvalue, line, col = tokens.next()
            if (tname, tvalue) == ('CHAR', ']'):
                return
            elif tname != 'S':
                raise ParseException('', line, col)
    
    while True:
        tname, tvalue, line, col = tokens.next()
        
        if tname == 'IDENT':
            property = tvalue
            
            while True:
                tname, tvalue, line, col = tokens.next()
                
                if (tname, tvalue) in [('CHAR', '<'), ('CHAR', '>')]:
                    _tname, _tvalue, line, col = tokens.next()
        
                    if (_tname, _tvalue) == ('CHAR', '='):
                        #
                        # One of <=, >=
                        #
                        op = tvalue + _tvalue
                        value = next_scalar(tokens)
                        finish_attribute(tokens)
                        return SelectorAttributeTest(property, op, value)
                    
                    else:
                        #
                        # One of <, > and we popped a token too early
                        #
                        op = tvalue
                        value = next_scalar(chain([(_tname, _tvalue, line, col)], tokens))
                        finish_attribute(tokens)
                        return SelectorAttributeTest(property, op, value)
                
                elif (tname, tvalue) == ('CHAR', '!'):
                    _tname, _tvalue, line, col = tokens.next()
        
                    if (_tname, _tvalue) == ('CHAR', '='):
                        #
                        # !=
                        #
                        op = tvalue + _tvalue
                        value = next_scalar(tokens)
                        finish_attribute(tokens)
                        return SelectorAttributeTest(property, op, value)
                    
                    else:
                        raise ParseException('', line, col)
                
                elif (tname, tvalue) == ('CHAR', '='):
                    #
                    # =
                    #
                    op = tvalue
                    value = next_scalar(tokens)
                    finish_attribute(tokens)
                    return SelectorAttributeTest(property, op, value)
                
                elif tname != 'S':
                    raise ParseException('', line, col)
        
        elif tname != 'S':
            raise ParseException('', line, col)

    raise ParseException('', line, col)
    
def post_block(tokens):

    while True:
        tname, tvalue, line, col = tokens.next()
        
        if tname == 'IDENT':
            _tname, _tvalue, line, col = tokens.next()
            
            if (_tname, _tvalue) == ('CHAR', ':'):
                print '    a.', tvalue
                
                while True:
                    tname, tvalue, line, col = tokens.next()
                    
                    if (tname, tvalue) == ('CHAR', ';'):
                        break
                    
                    elif tname != 'S':
                        print '    b.', tname, repr(tvalue)
                
            else:
                raise ParseException('', line, col)
        
        if (tname, tvalue) == ('CHAR', '}'):
            break

def post_rule(tokens, selectors):

    element = None
    elements = []
    
    while True:
        tname, tvalue, line, col = tokens.next()
        
        if tname == 'IDENT':
            #
            # Identifier always starts a new element.
            #
            element = SelectorElement()
            elements.append(element)
            element.addName(tvalue)
            
        elif tname == 'HASH':
            #
            # Hash is an ID selector:
            # http://www.w3.org/TR/CSS2/selector.html#id-selectors
            #
            if not element:
                element = SelectorElement()
                elements.append(element)
        
            element.addName(tvalue)
        
        elif (tname, tvalue) == ('CHAR', '.'):
            while True:
                tname, tvalue, line, col = tokens.next()
                
                if tname == 'IDENT':
                    #
                    # Identifier after a period is a class selector:
                    # http://www.w3.org/TR/CSS2/selector.html#class-html
                    #
                    if not element:
                        element = SelectorElement()
                        elements.append(element)
                
                    element.addName('.'+tvalue)
                    break
                
                else:
                    raise ParseException('', line, col)
        
        elif (tname, tvalue) == ('CHAR', '*'):
            #
            # Asterisk character is a universal selector:
            # http://www.w3.org/TR/CSS2/selector.html#universal-selector
            #
            if not element:
                element = SelectorElement()
                elements.append(element)
        
            element.addName(tvalue)

        elif (tname, tvalue) == ('CHAR', '['):
            #
            # Left-bracket is the start of an attribute selector:
            # http://www.w3.org/TR/CSS2/selector.html#attribute-selectors
            #
            test = post_attribute(tokens)
            element.addTest(test)
        
        elif (tname, tvalue) == ('CHAR', ','):
            #
            # Comma delineates one of a group of selectors:
            # http://www.w3.org/TR/CSS2/selector.html#grouping
            #
            # Recurse here.
            #
            selectors.append(Selector(*elements))
            return post_rule(tokens, selectors)
        
        elif (tname, tvalue) == ('CHAR', '{'):
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
