import re
from binascii import unhexlify as unhex
from itertools import chain, product

from cssutils.tokenize2 import Tokenizer as cssTokenizer

from cascadenik.style import color, color_transparent, uri, boolean, numbers, properties
from cascadenik.style import ParseException, Declaration, Selector, SelectorElement, SelectorAttributeTest, Property, Value

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
    line-width: 2 !important;
    line-dasharray: 3, 3;
}

* Stuff
{
    line-color: #f00;
}

"""

def parse_attribute(tokens):

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

def postprocess_value(property, tokens, important, line, col):
    
    if properties[property.name] in (int, float, str, color, uri, boolean) or type(properties[property.name]) is tuple:
        if len(tokens) != 1:
            raise ParseException('Single value only for property "%(property)s"' % locals(), line, col)

    if properties[property.name] is int:
        if tokens[0][0] != 'NUMBER':
            raise ParseException('Number value only for property "%(property)s"' % locals(), line, col)

        value = int(tokens[0][1])

    elif properties[property.name] is float:
        if tokens[0][0] != 'NUMBER':
            raise ParseException('Number value only for property "%(property)s"' % locals(), line, col)

        value = float(tokens[0][1])

    elif properties[property.name] is str:
        if tokens[0][0] != 'STRING':
            raise ParseException('String value only for property "%(property)s"' % locals(), line, col)

        value = str(tokens[0][1][1:-1])

    elif properties[property.name] is color_transparent:
        if tokens[0][0] != 'HASH' and (tokens[0][0] != 'IDENT' or tokens[0][1] != 'transparent'):
            raise ParseException('Hash or transparent value only for property "%(property)s"' % locals(), line, col)

        if tokens[0][0] == 'HASH':
            if not re.match(r'^#([0-9a-f]{3}){1,2}$', tokens[0][1], re.I):
                raise ParseException('Unrecognized color value for property "%(property)s"' % locals(), line, col)
    
            hex = tokens[0][1][1:]
            
            if len(hex) == 3:
                hex = hex[0]+hex[0] + hex[1]+hex[1] + hex[2]+hex[2]
            
            rgb = (ord(unhex(h)) for h in (hex[0:2], hex[2:4], hex[4:6]))
            
            value = color(*rgb)

        else:
            value = 'transparent'

    elif properties[property.name] is color:
        if tokens[0][0] != 'HASH':
            raise ParseException('Hash value only for property "%(property)s"' % locals(), line, col)

        if not re.match(r'^#([0-9a-f]{3}){1,2}$', tokens[0][1], re.I):
            raise ParseException('Unrecognized color value for property "%(property)s"' % locals(), line, col)

        hex = tokens[0][1][1:]
        
        if len(hex) == 3:
            hex = hex[0]+hex[0] + hex[1]+hex[1] + hex[2]+hex[2]
        
        rgb = (ord(unhex(h)) for h in (hex[0:2], hex[2:4], hex[4:6]))
        
        value = color(*rgb)

    elif properties[property.name] is uri:
        if tokens[0][0] != 'URI':
            raise ParseException('URI value only for property "%(property)s"' % locals(), line, col)

        raw = str(tokens[0][1])

        if raw.startswith('url("') and raw.endswith('")'):
            raw = raw[5:-2]
            
        elif raw.startswith("url('") and raw.endswith("')"):
            raw = raw[5:-2]
            
        elif raw.startswith('url(') and raw.endswith(')'):
            raw = raw[4:-1]

        value = uri(raw)
            
    elif properties[property.name] is boolean:
        if tokens[0][0] != 'IDENT' or tokens[0][1] not in ('true', 'false'):
            raise ParseException('true/false value only for property "%(property)s"' % locals(), line, col)

        value = boolean(tokens[0][1] == 'true')
            
    elif type(properties[property.name]) is tuple:
        if tokens[0][0] != 'IDENT':
            raise ParseException('Identifier value only for property "%(property)s"' % locals(), line, col)

        if tokens[0][1] not in properties[property.name]:
            raise ParseException('Unrecognized value for property "%(property)s"' % locals(), line, col)

        value = str(tokens[0][1])
            
    elif properties[property.name] is numbers:
        values = []
        
        # strip the list down to what we think goes number, comma, number, etc.
        relevant_tokens = [token for token in tokens
                           if token[0] == 'NUMBER' or token == ('CHAR', ',')]
        
        for (i, token) in enumerate(relevant_tokens):
            if (i % 2) == 0 and token[0] == 'NUMBER':
                try:
                    value = int(token[1])
                except ValueError:
                    value = float(token[1])

                values.append(value)

            elif (i % 2) == 1 and token[0] == 'CHAR':
                # fine, it's a comma
                continue

            else:
                raise ParseException('Value for property "%(property)s" should be a comma-delimited list of numbers' % locals(), line, col)

        value = numbers(*values)

    return Value(value, important)

def parse_block(tokens):
    """ Return an array of tuples: (property, value, (line, col), importance)
    """
    def parse_value(tokens):
        value = []
        while True:
            tname, tvalue, line, col = tokens.next()
            if (tname, tvalue) == ('CHAR', '!'):
                while True:
                    tname, tvalue, line, col = tokens.next()
                    if (tname, tvalue) == ('IDENT', 'important'):
                        while True:
                            tname, tvalue, line, col = tokens.next()
                            if (tname, tvalue) == ('CHAR', ';'):
                                #
                                # end of a high-importance value
                                #
                                return value, True
                            elif tname != 'S':
                                raise ParseException('', line, col)
                        break
                    else:
                        raise ParseException('', line, col)
                break
            elif (tname, tvalue) == ('CHAR', ';'):
                #
                # end of a low-importance value
                #
                return value, False
            elif tname != 'S':
                value.append((tname, tvalue))
        raise ParseException('', line, col)
    
    property_values = []
    
    while True:
        tname, tvalue, line, col = tokens.next()
        
        if tname == 'IDENT':
            _tname, _tvalue, _line, _col = tokens.next()
            
            if (_tname, _tvalue) == ('CHAR', ':'):
            
                if tvalue not in properties:
                    raise ParseException('', line, col)

                property = Property(tvalue)
                vtokens, importance = parse_value(tokens)
                value = postprocess_value(property, vtokens, importance, line, col)
                
                property_values.append((property, value, (line, col), importance))
                
            else:
                raise ParseException('', line, col)
        
        elif (tname, tvalue) == ('CHAR', '}'):
            return property_values
        
        elif tname != 'S':
            raise ParseException('', line, col)

    raise ParseException('', line, col)

def parse_rule(tokens, selectors):

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
            test = parse_attribute(tokens)
            element.addTest(test)
        
        elif (tname, tvalue) == ('CHAR', ','):
            #
            # Comma delineates one of a group of selectors:
            # http://www.w3.org/TR/CSS2/selector.html#grouping
            #
            # Recurse here.
            #
            selectors.append(Selector(*elements))
            return parse_rule(tokens, selectors)
        
        elif (tname, tvalue) == ('CHAR', '{'):
            #
            # Left-brace is the start of a block:
            # http://www.w3.org/TR/CSS2/syndata.html#block
            #
            # Return a full block here.
            #
            selectors.append(Selector(*elements))
            ruleset = []
            
            for (selector, property_value) in product(selectors, parse_block(tokens)):

                property, value, (line, col), importance = property_value
                sort_key = value.importance(), selector.specificity(), (line, col)

                ruleset.append(Declaration(selector, property, value, sort_key))
            
            return ruleset

print css

tokens = cssTokenizer().tokenize(css)

while True:
    print '-' * 20
    print parse_rule(tokens, [])
