import re
import operator
from itertools import chain, product
from binascii import unhexlify as unhex
from cssutils.tokenize2 import Tokenizer as cssTokenizer

from .style import properties, numbers, boolean, uri, color, color_transparent
from .style import Selector, SelectorElement, SelectorAttributeTest
from .style import Declaration, Property, Value

class ParseException(Exception):
    
    def __init__(self, msg, line, col):
        Exception.__init__(self, '%(msg)s (line %(line)d, column %(col)d)' % locals())

def stylesheet_declarations(string, is_merc=False):
    """ Parse a string representing a stylesheet into a list of declarations.
    
        Required boolean is_merc indicates whether the projection should
        be interpreted as spherical mercator, so we know what to do with
        zoom/scale-denominator in parse_rule().
    """
    declarations = []
    tokens = cssTokenizer().tokenize(string)
    
    while True:
        try:
            for declaration in parse_rule(tokens, [], is_merc):
                declarations.append(declaration)
        except StopIteration:
            break
    
    # sort by a css-like method
    return sorted(declarations, key=operator.attrgetter('sort_key'))

def parse_attribute(tokens, is_merc):
    """ Parse a token stream from inside an attribute selector.
    
        Enter this function after a left-bracket is found:
        http://www.w3.org/TR/CSS2/selector.html#attribute-selectors
    """
    #
    # Local helper functions
    #

    def next_scalar(tokens, op):
        """ Look for a scalar value just after an attribute selector operator.
        """
        while True:
            tname, tvalue, line, col = tokens.next()
            if tname == 'NUMBER':
                try:
                    value = int(tvalue)
                except ValueError:
                    value = float(tvalue)
                return value
            elif (tname, tvalue) == ('CHAR', '-'):
                tname, tvalue, line, col = tokens.next()
                if tname == 'NUMBER':
                    try:
                        value = int(tvalue)
                    except ValueError:
                        value = float(tvalue)
                    return -value
                else:
                    raise ParseException('Unexpected non-number after a minus sign', line, col)
            elif tname in ('STRING', 'IDENT'):
                if op in ('<', '<=', '=>', '>'):
                    raise ParseException('Selector attribute must use a number for comparison tests', line, col)
                if tname == 'STRING':
                    return tvalue[1:-1]
                else:
                    return tvalue
            elif tname != 'S':
                raise ParseException('Unexpected non-scalar token in attribute', line, col)
    
    def finish_attribute(tokens):
        """ Look for the end of an attribute selector operator.
        """
        while True:
            tname, tvalue, line, col = tokens.next()
            if (tname, tvalue) == ('CHAR', ']'):
                return
            elif tname != 'S':
                raise ParseException('Found something other than a closing right-bracket at the end of attribute', line, col)
    
    #
    # The work.
    #
    
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
                        # Operator is one of '<=', '>='
                        #
                        op = tvalue + _tvalue
                        value = next_scalar(tokens, op)
                        finish_attribute(tokens)
                        return SelectorAttributeTest(property, op, value)
                    
                    else:
                        #
                        # Operator is one of '<', '>' and we popped a token too early
                        #
                        op = tvalue
                        value = next_scalar(chain([(_tname, _tvalue, line, col)], tokens), op)
                        finish_attribute(tokens)
                        return SelectorAttributeTest(property, op, value)
                
                elif (tname, tvalue) == ('CHAR', '!'):
                    _tname, _tvalue, line, col = tokens.next()
        
                    if (_tname, _tvalue) == ('CHAR', '='):
                        #
                        # Operator is '!='
                        #
                        op = tvalue + _tvalue
                        value = next_scalar(tokens, op)
                        finish_attribute(tokens)
                        return SelectorAttributeTest(property, op, value)
                    
                    else:
                        raise ParseException('Malformed operator in attribute selector', line, col)
                
                elif (tname, tvalue) == ('CHAR', '='):
                    #
                    # Operator is '='
                    #
                    op = tvalue
                    value = next_scalar(tokens, op)
                    finish_attribute(tokens)
                    return SelectorAttributeTest(property, op, value)
                
                elif tname != 'S':
                    raise ParseException('Missing operator in attribute selector', line, col)
        
        elif tname != 'S':
            raise ParseException('Unexpected token in attribute selector', line, col)

    raise ParseException('Malformed attribute selector', line, col)

def postprocess_value(property, tokens, important, line, col):
    """ Convert a list of property value tokens into a single Value instance.
    
        Values can be numbers, strings, colors, uris, or booleans:
        http://www.w3.org/TR/CSS2/syndata.html#values
    """
    #
    # Helper function.
    #
    
    def combine_negative_numbers(tokens, line, col):
        """ Find negative numbers in a list of tokens, return a new list.
        
            Negative numbers come as two tokens, a minus sign and a number.
        """
        tokens, original_tokens = [], iter(tokens)
        
        while True:
            try:
                tname, tvalue = original_tokens.next()[:2]
                
                if (tname, tvalue) == ('CHAR', '-'):
                    tname, tvalue = original_tokens.next()[:2]
    
                    if tname == 'NUMBER':
                        # minus sign with a number is a negative number
                        tokens.append(('NUMBER', '-'+tvalue))
                    else:
                        raise ParseException('Unexpected non-number after a minus sign', line, col)
    
                else:
                    tokens.append((tname, tvalue))
    
            except StopIteration:
                break
        
        return tokens
    
    #
    # The work.
    #
    
    tokens = combine_negative_numbers(tokens, line, col)
    
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
    """ Parse a token stream into an array of declaration tuples.
    
        Return an array of (property, value, (line, col), importance).
    
        Enter this function after a left-brace is found:
        http://www.w3.org/TR/CSS2/syndata.html#block
    """
    #
    # Local helper functions
    #

    def parse_value(tokens):
        """ Look for value tokens after a property name, possibly !important.
        """
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
                            elif tname not in ('S', 'COMMENT'):
                                raise ParseException('Unexpected values after !important declaration', line, col)
                        break
                    else:
                        raise ParseException('Malformed declaration after "!"', line, col)
                break
            elif (tname, tvalue) == ('CHAR', ';'):
                #
                # end of a low-importance value
                #
                return value, False
            elif tname not in ('S', 'COMMENT'):
                value.append((tname, tvalue))
        raise ParseException('Malformed property value', line, col)
    
    #
    # The work.
    #
    
    property_values = []
    
    while True:
        tname, tvalue, line, col = tokens.next()
        
        if tname == 'IDENT':
            _tname, _tvalue, _line, _col = tokens.next()
            
            if (_tname, _tvalue) == ('CHAR', ':'):
            
                if tvalue not in properties:
                    raise ParseException('Unsupported property name, %s' % tvalue, line, col)

                property = Property(tvalue)
                vtokens, importance = parse_value(tokens)
                value = postprocess_value(property, vtokens, importance, line, col)
                
                property_values.append((property, value, (line, col), importance))
                
            else:
                raise ParseException('Malformed property name', line, col)
        
        elif (tname, tvalue) == ('CHAR', '}'):
            return property_values
        
        elif tname not in ('S', 'COMMENT'):
            raise ParseException('Malformed style rule', line, col)

    raise ParseException('Malformed block', line, col)

def parse_rule(tokens, selectors, is_merc):
    """ Parse a rule set, return a list of declarations.
        
        A rule set is a combination of selectors and declarations:
        http://www.w3.org/TR/CSS2/syndata.html#rule-sets
    
        To handle groups of selectors, use recursion:
        http://www.w3.org/TR/CSS2/selector.html#grouping
    """
    #
    # Local helper function
    #

    def validate_selector_elements(elements, line, col):
        if len(elements) > 2:
            raise ParseException('Only two-element selectors are supported for Mapnik styles', line, col)
    
        if len(elements) == 0:
            raise ParseException('At least one element must be present in selectors for Mapnik styles', line, col)
    
        if elements[0].names[0] not in ('Map', 'Layer') and elements[0].names[0][0] not in ('.', '#', '*'):
            raise ParseException('All non-ID, non-class first elements must be "Layer" Mapnik styles', line, col)
        
        if len(elements) == 2 and elements[1].countTests():
            raise ParseException('Only the first element in a selector may have attributes in Mapnik styles', line, col)
    
        if len(elements) == 2 and elements[1].countIDs():
            raise ParseException('Only the first element in a selector may have an ID in Mapnik styles', line, col)
    
        if len(elements) == 2 and elements[1].countClasses():
            raise ParseException('Only the first element in a selector may have a class in Mapnik styles', line, col)
    
    #
    # The work.
    #
    
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
                    raise ParseException('Malformed class selector', line, col)
        
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
            test = parse_attribute(tokens, is_merc)
            element.addTest(test)
        
        elif (tname, tvalue) == ('CHAR', ','):
            #
            # Comma delineates one of a group of selectors:
            # http://www.w3.org/TR/CSS2/selector.html#grouping
            #
            # Recurse here.
            #
            selectors.append(Selector(*elements))
            selectors[-1].convertZoomTests(is_merc)
            return parse_rule(tokens, selectors, is_merc)
        
        elif (tname, tvalue) == ('CHAR', '{'):
            #
            # Left-brace is the start of a block:
            # http://www.w3.org/TR/CSS2/syndata.html#block
            #
            # Return a full block here.
            #
            validate_selector_elements(elements, line, col)
            selectors.append(Selector(*elements))
            selectors[-1].convertZoomTests(is_merc)
            ruleset = []
            
            for (selector, property_value) in product(selectors, parse_block(tokens)):

                property, value, (line, col), importance = property_value
                sort_key = value.importance(), selector.specificity(), (line, col)

                ruleset.append(Declaration(selector, property, value, sort_key))
            
            return ruleset
