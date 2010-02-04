import re
import sys
import os.path
import urlparse
import operator
from binascii import unhexlify as unhex

# monkey with sys.path due to some weirdness inside cssutils
sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from cssutils.tokenize2 import Tokenizer as cssTokenizer

class color:
    def __init__(self, r, g, b):
        self.channels = r, g, b

    def __repr__(self):
        return '#%02x%02x%02x' % self.channels

    def __str__(self):
        return repr(self)

class color_transparent:
    def __init__(self, r, g, b):
        self.channels = r, g, b

    def __repr__(self):
        return '#%02x%02x%02x' % self.channels

    def __str__(self):
        return repr(self)

class uri:
    def __init__(self, address, base=None):
        if base:
            self.address = urlparse.urljoin(base, address)
        else:
            self.address = address

    def __repr__(self):
        return str(self.address) #'url("%(address)s")' % self.__dict__

    def __str__(self):
        return repr(self)

class boolean:
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        if self.value:
            return 'true'
        else:
            return 'false'

    def __str__(self):
        return repr(self)

class numbers:
    def __init__(self, *values):
        self.values = values

    def __repr__(self):
        return ','.join(map(str, self.values))

    def __str__(self):
        return repr(self)

# recognized properties

properties = {
    #--------------- map

    # 
    'map-bgcolor': color_transparent,

    #--------------- polygon symbolizer

    # 
    'polygon-fill': color,

    # 
    'polygon-gamma': float,

    # 
    'polygon-opacity': float,

    #--------------- line symbolizer

    # CSS colour (default "black")
    'line-color': color,

    # 0.0 - n (default 1.0)
    'line-width': float,

    # 0.0 - 1.0 (default 1.0)
    'line-opacity': float,

    # miter, round, bevel (default miter)
    'line-join': ('miter', 'round', 'bevel'),

    # round, butt, square (default butt)
    'line-cap': ('butt', 'round', 'square'),

    # d0,d1, ... (default none)
    'line-dasharray': numbers, # Number(s)

    #--------------- line symbolizer for outlines

    # CSS colour (default "black")
    'outline-color': color,

    # 0.0 - n (default 1.0)
    'outline-width': float,

    # 0.0 - 1.0 (default 1.0)
    'outline-opacity': float,

    # miter, round, bevel (default miter)
    'outline-join': ('miter', 'round', 'bevel'),

    # round, butt, square (default butt)
    'outline-cap': ('butt', 'round', 'square'),

    # d0,d1, ... (default none)
    'outline-dasharray': numbers, # Number(s)

    #--------------- line symbolizer for inlines

    # CSS colour (default "black")
    'inline-color': color,

    # 0.0 - n (default 1.0)
    'inline-width': float,

    # 0.0 - 1.0 (default 1.0)
    'inline-opacity': float,

    # miter, round, bevel (default miter)
    'inline-join': ('miter', 'round', 'bevel'),

    # round, butt, square (default butt)
    'inline-cap': ('butt', 'round', 'square'),

    # d0,d1, ... (default none)
    'inline-dasharray': numbers, # Number(s)

    #--------------- text symbolizer

    # Font name
    'text-face-name': str,

    # Font size
    'text-size': int,

    # ?
    'text-ratio': None, # ?

    # length before wrapping long names
    'text-wrap-width': int,

    # space between repeated labels
    'text-spacing': int,

    # Horizontal spacing between characters (in pixels).
    'text-character-spacing': int,

    # Vertical spacing between lines of multiline labels (in pixels)
    'text-line-spacing': int,

    # allow labels to be moved from their point
    'text-label-position-tolerance': None, # ?

    # Maximum angle (in degrees) between two consecutive characters in a label allowed (to stop placing labels around sharp corners)
    'text-max-char-angle-delta': int,

    # Color of the fill ie #FFFFFF
    'text-fill': color,

    # Color of the halo
    'text-halo-fill': color,

    # Radius of the halo in whole pixels, fractional pixels are not accepted
    'text-halo-radius': int,

    # displace label by fixed amount on either axis.
    'text-dx': int,
    'text-dy': int,

    # Boolean to avoid labeling near intersection edges.
    'text-avoid-edges': boolean,

    # Minimum distance between repeated labels such as street names or shield symbols
    'text-min-distance': int,

    # Allow labels to overlap other labels
    'text-allow-overlap': boolean,

    # "line" to label along lines instead of by point
    'text-placement': ('point', 'line'),

    #--------------- point symbolizer

    # path to image file
    'point-file': uri, # none

    # px (default 4), generally omit this and let PIL handle it
    'point-width': int,
    'point-height': int,

    # image type: png or tiff, omitted thanks to PIL
    'point-type': None,

    # true/false
    'point-allow-overlap': boolean,

    #--------------- polygon pattern symbolizer

    # path to image file (default none)
    'polygon-pattern-file': uri,

    # px (default 4), generally omit this and let PIL handle it
    'polygon-pattern-width': int,
    'polygon-pattern-height': int,

    # image type: png or tiff, omitted thanks to PIL
    'polygon-pattern-type': None,

    #--------------- line pattern symbolizer

    # path to image file (default none)
    'line-pattern-file': uri,

    # px (default 4), generally omit this and let PIL handle it
    'line-pattern-width': int,
    'line-pattern-height': int,

    # image type: png or tiff, omitted thanks to PIL
    'line-pattern-type': None,

    #--------------- shield symbolizer

    # 
    'shield-name': None, # (use selector for this)

    # 
    'shield-face-name': str,

    # 
    'shield-size': int,

    # 
    'shield-fill': color,

    # Minimum distance between repeated labels such as street names or shield symbols
    'shield-min-distance': int,

    # Spacing between repeated labels such as street names or shield symbols
    'shield-spacing': int,

    # Horizontal spacing between characters (in pixels).
    'shield-character-spacing': int,
    
    # Vertical spacing between lines of multiline shields (in pixels)
    'shield-line-spacing': int,

    # path to image file (default none)
    'shield-file': uri,

    # px (default 4), generally omit this and let PIL handle it
    'shield-width': int,
    'shield-height': int,

    # image type: png or tiff, omitted thanks to PIL
    'shield-type': None
}

class ParseException(Exception):
    
    def __init__(self, msg, line, col):
        Exception.__init__(self, '%(msg)s (line %(line)d, column %(col)d)' % locals())

class Declaration:
    """ Bundle with a selector, single property and value.
    """
    def __init__(self, selector, property, value, sort_key):
        self.selector = selector
        self.property = property
        self.value = value
        self.sort_key = sort_key

    def __repr__(self):
        return '%(selector)s { %(property)s: %(value)s }' % self.__dict__

class Selector:
    """ Represents a complete selector with elements and attribute checks.
    """
    def __init__(self, *elements):
        assert len(elements) in (1, 2)
        assert elements[0].names[0] in ('Map', 'Layer') or elements[0].names[0][0] in ('.', '#', '*')
        assert len(elements) == 1 or not elements[1].countTests()
        assert len(elements) == 1 or not elements[1].countIDs()
        assert len(elements) == 1 or not elements[1].countClasses()
    
        self.elements = elements[:]

    def convertZoomTests(self):
        """ Modify the tests on this selector to use mapnik-friendly
            scale-denominator instead of shorthand zoom.
        """
        # somewhat-fudged values for mapniks' scale denominator at a range
        # of zoom levels when using the Google/VEarth mercator projection.
        zooms = {
             1: (200000000, 500000000),
             2: (100000000, 200000000),
             3: (50000000, 100000000),
             4: (25000000, 50000000),
             5: (12500000, 25000000),
             6: (6500000, 12500000),
             7: (3000000, 6500000),
             8: (1500000, 3000000),
             9: (750000, 1500000),
            10: (400000, 750000),
            11: (200000, 400000),
            12: (100000, 200000),
            13: (50000, 100000),
            14: (25000, 50000),
            15: (12500, 25000),
            16: (5000, 12500),
            17: (2500, 5000),
            18: (1000, 2500)
            }
        
        for test in self.elements[0].tests:
            if test.property == 'zoom':
                test.property = 'scale-denominator'

                if test.op == '=':
                    # zoom level equality implies two tests, so we add one and modify one
                    self.elements[0].addTest(SelectorAttributeTest('scale-denominator', '<', max(zooms[test.value])))
                    test.op, test.value = '>=', min(zooms[test.value])

                elif test.op == '<':
                    test.op, test.value = '>=', max(zooms[test.value])
                elif test.op == '<=':
                    test.op, test.value = '>=', min(zooms[test.value])
                elif test.op == '>=':
                    test.op, test.value = '<', max(zooms[test.value])
                elif test.op == '>':
                    test.op, test.value = '<', min(zooms[test.value])
                    

    def specificity(self):
        """ Loosely based on http://www.w3.org/TR/REC-CSS2/cascade.html#specificity
        """
        ids = sum(a.countIDs() for a in self.elements)
        non_ids = sum((a.countNames() - a.countIDs()) for a in self.elements)
        tests = sum(len(a.tests) for a in self.elements)
        
        return (ids, non_ids, tests)

    def matches(self, tag, id, classes):
        """ Given an id and a list of classes, return True if this selector would match.
        """
        element = self.elements[0]
        unmatched_ids = [name[1:] for name in element.names if name.startswith('#')]
        unmatched_classes = [name[1:] for name in element.names if name.startswith('.')]
        unmatched_tags = [name for name in element.names if name is not '*' and not name.startswith('#') and not name.startswith('.')]
        
        if tag and tag in unmatched_tags:
            unmatched_tags.remove(tag)

        if id and id in unmatched_ids:
            unmatched_ids.remove(id)

        for class_ in classes:
            if class_ in unmatched_classes:
                unmatched_classes.remove(class_)
        
        if unmatched_tags or unmatched_ids or unmatched_classes:
            return False

        else:
            return True
    
    def isRanged(self):
        """
        """
        return bool(self.rangeTests())
    
    def rangeTests(self):
        """
        """
        return [test for test in self.allTests() if test.isRanged()]
    
    def isMapScaled(self):
        """
        """
        return bool(self.mapScaleTests())
    
    def mapScaleTests(self):
        """
        """
        return [test for test in self.allTests() if test.isMapScaled()]
    
    def allTests(self):
        """
        """
        tests = []
        
        for test in self.elements[0].tests:
            tests.append(test)

        return tests
    
    def inRange(self, value):
        """
        """
        for test in self.rangeTests():
            if not test.inRange(value):
                return False

        return True

    def __repr__(self):
        return ' '.join(repr(a) for a in self.elements)

class SelectorElement:
    """ One element in selector, with names and tests.
    """
    def __init__(self, names=None, tests=None):
        if names:
            self.names = names
        else:
            self.names = []

        if tests:
            self.tests = tests
        else:
            self.tests = []

    def addName(self, name):
        self.names.append(name)
    
    def addTest(self, test):
        self.tests.append(test)

    def countTests(self):
        return len(self.tests)
    
    def countIDs(self):
        return len([n for n in self.names if n.startswith('#')])
    
    def countNames(self):
        return len(self.names)
    
    def countClasses(self):
        return len([n for n in self.names if n.startswith('.')])
    
    def __repr__(self):
        return ''.join(self.names) + ''.join(repr(t) for t in self.tests)

class SelectorAttributeTest:
    """ Attribute test for a Selector, i.e. the part that looks like "[foo=bar]"
    """
    def __init__(self, property, op, value):
        assert op in ('<', '<=', '=', '!=', '>=', '>')
        self.op = op
        self.property = property
        self.value = value

    def __repr__(self):
        return '[%(property)s%(op)s%(value)s]' % self.__dict__

    def __cmp__(self, other):
        """
        """
        return cmp(unicode(self), unicode(other))

    def isSimple(self):
        """
        """
        return self.op in ('=', '!=') and not self.isRanged()
    
    def inverse(self):
        """
        
            TODO: define this for non-simple tests.
        """
        assert self.isSimple(), 'inverse() is only defined for simple tests'
        
        if self.op == '=':
            return SelectorAttributeTest(self.property, '!=', self.value)
        
        elif self.op == '!=':
            return SelectorAttributeTest(self.property, '=', self.value)
    
    def isNumeric(self):
        """
        """
        return type(self.value) in (int, float)
    
    def isRanged(self):
        """
        """
        return self.op in ('<', '<=', '>=', '>')
    
    def isMapScaled(self):
        """
        """
        return self.property == 'scale-denominator'
    
    def inRange(self, scale_denominator):
        """
        """
        if not self.isRanged():
            # always in range
            return True

        elif self.op == '>' and scale_denominator > self.value:
            return True

        elif self.op == '>=' and scale_denominator >= self.value:
            return True

        elif self.op == '=' and scale_denominator == self.value:
            return True

        elif self.op == '<=' and scale_denominator <= self.value:
            return True

        elif self.op == '<' and scale_denominator < self.value:
            return True

        return False

    def isCompatible(self, tests):
        """ Given a collection of tests, return false if this test contradicts any of them.
        """
        # print '?', self, tests
        
        for test in tests:
            if self.property == test.property:
                if self.op == '=':
                    if test.op == '=' and self.value != test.value:
                        return False
    
                    if test.op == '!=' and self.value == test.value:
                        return False
    
                    if test.op == '<' and self.value >= test.value:
                        return False
                
                    if test.op == '>' and self.value <= test.value:
                        return False
                
                    if test.op == '<=' and self.value > test.value:
                        return False
                
                    if test.op == '>=' and self.value < test.value:
                        return False
            
                if self.op == '!=':
                    if test.op == '=' and self.value == test.value:
                        return False
    
                    if test.op == '!=':
                        pass
    
                    if test.op == '<':
                        pass
                
                    if test.op == '>':
                        pass
                
                    if test.op == '<=' and self.value == test.value:
                        return False
                
                    if test.op == '>=' and self.value == test.value:
                        return False
            
                if self.op == '<':
                    if test.op == '=' and self.value <= test.value:
                        return False
    
                    if test.op == '!=':
                        return False
    
                    if test.op == '<':
                        pass
                
                    if test.op == '>' and self.value <= test.value:
                        return False
                
                    if test.op == '<=':
                        pass
                
                    if test.op == '>=' and self.value <= test.value:
                        return False
            
                if self.op == '>':
                    if test.op == '=' and self.value >= test.value:
                        return False
    
                    if test.op == '!=':
                        return False
    
                    if test.op == '<' and self.value >= test.value:
                        return False
                
                    if test.op == '>':
                        pass
                
                    if test.op == '<=' and self.value >= test.value:
                        return False
                
                    if test.op == '>=':
                        pass
            
                if self.op == '<=':
                    if test.op == '=' and self.value < test.value:
                        return False
    
                    if test.op == '!=' and self.value == test.value:
                        return False
    
                    if test.op == '<':
                        pass
                
                    if test.op == '>' and self.value <= test.value:
                        return False
                
                    if test.op == '<=':
                        pass
                
                    if test.op == '>=' and self.value < test.value:
                        return False
            
                if self.op == '>=':
                    if test.op == '=' and self.value > test.value:
                        return False
    
                    if test.op == '!=' and self.value == test.value:
                        return False
    
                    if test.op == '<' and self.value >= test.value:
                        return False
                
                    if test.op == '>':
                        pass
                
                    if test.op == '<=' and self.value > test.value:
                        return False
                
                    if test.op == '>=':
                        pass

        return True
    
    def rangeOpEdge(self):
        ops = {'<': operator.lt, '<=': operator.le, '=': operator.eq, '>=': operator.ge, '>': operator.gt}
        return ops[self.op], self.value

        return None

class Property:
    """ A style property.
    """
    def __init__(self, name):
        assert name in properties
    
        self.name = name

    def group(self):
        return self.name.split('-')[0]
    
    def __repr__(self):
        return self.name

    def __str__(self):
        return repr(self)

class Value:
    """ A style value.
    """
    def __init__(self, value, important):
        self.value = value
        self.important = important

    def importance(self):
        return int(self.important)
    
    def __repr__(self):
        return repr(self.value)

    def __str__(self):
        return unicode(self.value)

def stylesheet_declarations(string, base=None, is_gym=False):
    """
    """
    return rulesets_declarations(stylesheet_rulesets(string, base, is_gym))

def stylesheet_rulesets(string, base=None, is_gym=False):
    """ Parse a string representing a stylesheet into a list of rulesets.
    
        Optionally, accept a base string so we know where linked files come from,
        and a flag letting us know whether this is a Google/VEarth mercator projection
        so we know what to do with zoom/scale-denominator in postprocess_selector().
    """
    in_selectors = False
    in_block = False
    in_declaration = False # implies in_block
    in_property = False # implies in_declaration
    
    rulesets = []
    tokens = cssTokenizer().tokenize(string)
    
    for token in tokens:
        nname, value, line, col = token
        
        try:
            if not in_selectors and not in_block:
                if nname == 'CHAR' and value == '{':
                    # 
                    raise ParseException('Encountered unexpected opening "{"', line, col)

                elif (nname in ('IDENT', 'HASH')) or (nname == 'CHAR' and value != '{'):
                    # beginning of a 
                    rulesets.append({'selectors': [[(nname, value)]], 'declarations': []})
                    in_selectors = True
                    
            elif in_selectors and not in_block:
                ruleset = rulesets[-1]
            
                if (nname == 'CHAR' and value == '{'):
                    # open curly-brace means we're on to the actual rule sets
                    ruleset['selectors'][-1] = postprocess_selector(ruleset['selectors'][-1], is_gym, line, col)
                    in_selectors = False
                    in_block = True
    
                elif (nname == 'CHAR' and value == ','):
                    # comma means there's a break between selectors
                    ruleset['selectors'][-1] = postprocess_selector(ruleset['selectors'][-1], is_gym, line, col)
                    ruleset['selectors'].append([])
    
                elif nname not in ('COMMENT'):
                    # we're just in a selector is all
                    ruleset['selectors'][-1].append((nname, value))
    
            elif in_block and not in_declaration:
                ruleset = rulesets[-1]
            
                if nname == 'IDENT':
                    # right at the start of a declaration
                    ruleset['declarations'].append({'property': [(nname, value)], 'value': [], 'position': (line, col)})
                    in_declaration = True
                    in_property = True
                    
                elif (nname == 'CHAR' and value == '}'):
                    # end of block
                    in_block = False

                elif nname not in ('S', 'COMMENT'):
                    # something else
                    raise ParseException('Unexpected %(nname)s while looking for a property' % locals(), line, col)
    
            elif in_declaration and in_property:
                declaration = rulesets[-1]['declarations'][-1]
            
                if nname == 'CHAR' and value == ':':
                    # end of property
                    declaration['property'] = postprocess_property(declaration['property'], line, col)
                    in_property = False
    
                elif nname not in ('COMMENT'):
                    # in a declaration property
                    declaration['property'].append((nname, value))
    
            elif in_declaration and not in_property:
                declaration = rulesets[-1]['declarations'][-1]
            
                if nname == 'CHAR' and value == ';':
                    # end of declaration
                    declaration['value'] = postprocess_value(declaration['value'], declaration['property'], base, line, col)
                    in_declaration = False
    
                elif nname not in ('COMMENT'):
                    # in a declaration value
                    declaration['value'].append((nname, value))

        except ParseException, e:
            #raise ParseException(e.message + ' (line %(line)d, column %(col)d)' % locals(), line, col)
            raise

    return rulesets

def rulesets_declarations(rulesets):
    """ Convert a list of rulesets (as returned by stylesheet_rulesets)
        into an ordered list of individual selectors and declarations.
    """
    declarations = []
    
    for ruleset in rulesets:
        for declaration in ruleset['declarations']:
            for selector in ruleset['selectors']:
                declarations.append(Declaration(selector, declaration['property'], declaration['value'],
                                                (declaration['value'].importance(), selector.specificity(), declaration['position'])))

    # sort by a css-like method
    return sorted(declarations, key=operator.attrgetter('sort_key'))

def trim_extra(tokens):
    """ Trim comments and whitespace from each end of a list of tokens.
    """
    if len(tokens) == 0:
        return tokens
    
    while tokens[0][0] in ('S', 'COMMENT'):
        tokens = tokens[1:]

    while tokens[-1][0] in ('S', 'COMMENT'):
        tokens = tokens[:-1]
        
    return tokens

def postprocess_selector(tokens, is_gym, line=0, col=0):
    """ Convert a list of tokens into a Selector.
    """
    tokens = (token for token in trim_extra(tokens))
    
    elements = []
    parts = []
    
    in_element = False
    in_attribute = False
    
    for token in tokens:
        nname, value = token
        
        if not in_element:
            if (nname == 'CHAR' and value in ('.', '*')) or nname in ('IDENT', 'HASH'):
                elements.append(SelectorElement())
                in_element = True
                # continue on to if in_element below...

        if in_element and not in_attribute:
            if nname == 'CHAR' and value == '.':
                next_nname, next_value = tokens.next()
                
                if next_nname == 'IDENT':
                    elements[-1].addName(value + next_value)
                
            elif nname in ('IDENT', 'HASH') or (nname == 'CHAR' and value == '*'):
                elements[-1].addName(value)

            elif nname == 'CHAR' and value == '[':
                in_attribute = True

            elif nname == 'S':
                in_element = False
                
        elif in_attribute:
            if nname in ('IDENT', 'NUMBER', 'STRING'):
                parts.append(value)
                
            elif nname == 'CHAR' and value in ('<', '=', '>', '!'):
                if value == '=' and parts[-1] in ('<', '>', '!'):
                    parts[-1] += value
                else:
                    if len(parts) != 1:
                        raise ParseException('Comparison operator must be in the middle of selector attribute', line, col)
                
                    parts.append(value)

            elif nname == 'CHAR' and value == ']':
                if len(parts) != 3:
                    raise ParseException('Incorrect number of items in selector attribute', line, col)

                args = parts[-3:]
                parts = []

                try:
                    args[2] = int(args[2])
                except ValueError:
                    try:
                        args[2] = float(args[2])
                    except ValueError:
                        if args[1] in ('<', '<=', '=>', '>'):
                            raise ParseException('Selector attribute must use a number for comparison tests', line, col)
                        elif args[2].startswith('"') and args[2].endswith('"'):
                            args[2] = args[2][1:-1]
                        elif args[2].startswith("'") and args[2].endswith("'"):
                            args[2] = args[2][1:-1]
                        else:
                            pass
                
                elements[-1].addTest(SelectorAttributeTest(*args))
                in_attribute = False

            elif nname == 'CHAR' and value == ']':
                in_attribute = False
    
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

    selector = Selector(*elements)
    
    if is_gym:
        selector.convertZoomTests()
    
    return selector

def postprocess_property(tokens, line=0, col=0):
    """ Convert a one-element list of tokens into a Property.
    """
    tokens = trim_extra(tokens)
    
    if len(tokens) != 1:
        raise ParseException('Too many tokens in property: ' + repr(tokens), line, col)
    
    if tokens[0][0] != 'IDENT':
        raise ParseException('Incorrect type of token in property: ' + repr(tokens), line, col)
    
    if tokens[0][1] not in properties:
        raise ParseException('"%s" is not a recognized property name' % tokens[0][1], line, col)
    
    return Property(tokens[0][1])

def postprocess_value(tokens, property, base=None, line=0, col=0):
    """
    """
    tokens = trim_extra(tokens)
    
    if len(tokens) >= 2 and (tokens[-2] == ('CHAR', '!')) and (tokens[-1] == ('IDENT', 'important')):
        important = True
        tokens = trim_extra(tokens[:-2])

    else:
        important = False
    
    if properties[property.name] in (int, float) and len(tokens) == 2 and tokens[0] == ('CHAR', '-') and tokens[1][0] == 'NUMBER':
        # put the negative sign on the number
        tokens = [(tokens[1][0], '-' + tokens[1][1])]
    
    value = tokens
    
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

        value = tokens[0][1][1:-1]

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

        raw = tokens[0][1]

        if raw.startswith('url("') and raw.endswith('")'):
            raw = raw[5:-2]
            
        elif raw.startswith("url('") and raw.endswith("')"):
            raw = raw[5:-2]
            
        elif raw.startswith('url(') and raw.endswith(')'):
            raw = raw[4:-1]

        value = uri(raw, base)
            
    elif properties[property.name] is boolean:
        if tokens[0][0] != 'IDENT' or tokens[0][1] not in ('true', 'false'):
            raise ParseException('true/false value only for property "%(property)s"' % locals(), line, col)

        value = boolean(tokens[0][1] == 'true')
            
    elif type(properties[property.name]) is tuple:
        if tokens[0][0] != 'IDENT':
            raise ParseException('Identifier value only for property "%(property)s"' % locals(), line, col)

        if tokens[0][1] not in properties[property.name]:
            raise ParseException('Unrecognized value for property "%(property)s"' % locals(), line, col)

        value = tokens[0][1]
            
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
