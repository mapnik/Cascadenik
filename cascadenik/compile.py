import os, sys
import re
import math
import pprint
import urllib
import urlparse
import tempfile
import StringIO
import operator
from operator import lt, le, eq, ge, gt
import xml.etree.ElementTree
from xml.etree.ElementTree import Element
import style
import PIL.Image

def main(file, dir):
    """ Given an input layers file and a directory, print the compiled
        XML file to stdout and save any encountered external image files
        to the named directory.
    """
    print compile(file, dir)
    return 0

counter = 0

opsort = {lt: 1, le: 2, eq: 3, ge: 4, gt: 5}
opstr = {lt: '<', le: '<=', eq: '==', ge: '>=', gt: '>'}
    
class Range:
    """ Represents a range for use in min/max scale denominator.
    
        Ranges can have a left side, a right side, neither, or both,
        with sides specified as inclusive or exclusive.
    """
    def __init__(self, leftop=None, leftedge=None, rightop=None, rightedge=None):
        assert leftop in (lt, le, eq, ge, gt, None)
        assert rightop in (lt, le, eq, ge, gt, None)

        self.leftop = leftop
        self.rightop = rightop
        self.leftedge = leftedge
        self.rightedge = rightedge

    def midpoint(self):
        """ Return a point guranteed to fall within this range, hopefully near the middle.
        """
        minpoint = self.leftedge

        if self.leftop is gt:
            minpoint += 1
    
        maxpoint = self.rightedge

        if self.rightop is lt:
            maxpoint -= 1

        if minpoint is None:
            return maxpoint
            
        elif maxpoint is None:
            return minpoint
            
        else:
            return (minpoint + maxpoint) / 2

    def isOpen(self):
        """ Return true if this range has any room in it.
        """
        if self.leftedge and self.rightedge and self.leftedge > self.rightedge:
            return False
    
        if self.leftedge == self.rightedge:
            if self.leftop is gt or self.rightop is lt:
                return False

        return True
    
    def __repr__(self):
        """
        """
        if self.leftedge == self.rightedge and self.leftop is ge and self.rightop is le:
            # equivalent to ==
            return '(=%s)' % self.leftedge
    
        try:
            return '(%s%s ... %s%s)' % (self.leftedge, opstr[self.leftop], opstr[self.rightop], self.rightedge)
        except KeyError:
            try:
                return '(... %s%s)' % (opstr[self.rightop], self.rightedge)
            except KeyError:
                try:
                    return '(%s%s ...)' % (self.leftedge, opstr[self.leftop])
                except KeyError:
                    return '(...)'

class Filter:
    """ Represents a filter of some sort for use in stylesheet rules.
    
        Composed of a list of tests.
    """
    def __init__(self, *tests):
        self.tests = list(tests)

    def isOpen(self):
        """ Return true if this filter is not trivially false, i.e. self-contradictory.
        """
        equals = {}
        nequals = {}
        
        for test in self.tests:
            if test.op == '=':
                if equals.has_key(test.arg1) and test.arg2 != equals[test.arg1]:
                    # we've already stated that this arg must equal something else
                    return False
                    
                if nequals.has_key(test.arg1) and test.arg2 in nequals[test.arg1]:
                    # we've already stated that this arg must not equal its current value
                    return False
                    
                equals[test.arg1] = test.arg2
        
            if test.op == '!=':
                if equals.has_key(test.arg1) and test.arg2 == equals[test.arg1]:
                    # we've already stated that this arg must equal its current value
                    return False
                    
                if not nequals.has_key(test.arg1):
                    nequals[test.arg1] = set()

                nequals[test.arg1].add(test.arg2)
        
        return True

    def clone(self):
        """
        """
        return Filter(*self.tests[:])
    
    def minusExtras(self):
        """ Return a new Filter that's equal to this one,
            without extra terms that don't add meaning.
        """
        assert self.isOpen()
        
        trimmed = self.clone()
        
        equals = {}
        
        for test in trimmed.tests:
            if test.op == '=':
                equals[test.arg1] = test.arg2

        extras = []

        for (i, test) in enumerate(trimmed.tests):
            if test.op == '!=' and equals.has_key(test.arg1) and equals[test.arg1] != test.arg2:
                extras.append(i)

        while extras:
            trimmed.tests.pop(extras.pop())

        return trimmed
    
    def __repr__(self):
        """
        """
        return ''.join(map(repr, sorted(self.tests)))
    
    def __cmp__(self, other):
        """
        """
        return cmp(repr(self), repr(other))

def selectors_ranges(selectors):
    """ Given a list of selectors and a map, return a list of Ranges that
        fully describes all possible unique slices within those selectors.
        
        If the map looks like it uses the well-known Google/VEarth maercator
        projection, accept "zoom" attributes in place of "scale-denominator".
        
        This function was hard to write, it should be hard to read.
        
        TODO: make this work for <= following by >= in breaks
    """
    repeated_breaks = []
    
    # start by getting all the range edges from the selectors into a list of break points
    for selector in selectors:
        for test in selector.rangeTests():
            repeated_breaks.append(test.rangeOpEdge())
    
    # from here on out, *order will matter*
    # it's expected that the breaks will be sorted from minimum to maximum,
    # with greater/lesser/equal operators accounted for.
    repeated_breaks.sort(key=lambda (o, e): (e, opsort[o]))
    
    breaks = []

    # next remove repetitions from the list
    for (i, (op, edge)) in enumerate(repeated_breaks):
        if i > 0:
            if op is repeated_breaks[i - 1][0] and edge == repeated_breaks[i - 1][1]:
                continue

        breaks.append(repeated_breaks[i])

    ranges = []
    
    # now turn those breakpoints into a list of ranges
    for (i, (op, edge)) in enumerate(breaks):
        if i == 0:
            # get a right-boundary for the first range
            if op in (lt, le):
                ranges.append(Range(None, None, op, edge))
            elif op in (eq, ge):
                ranges.append(Range(None, None, lt, edge))
            elif op is gt:
                ranges.append(Range(None, None, le, edge))

        elif i > 0:
            # get a left-boundary based on the previous right-boundary
            if ranges[-1].rightop is lt:
                ranges.append(Range(ge, ranges[-1].rightedge))
            else:
                ranges.append(Range(gt, ranges[-1].rightedge))

            # get a right-boundary for the current range
            if op in (lt, le):
                ranges[-1].rightop, ranges[-1].rightedge = op, edge
            elif op in (eq, ge):
                ranges[-1].rightop, ranges[-1].rightedge = lt, edge
            elif op is gt:
                ranges[-1].rightop, ranges[-1].rightedge = le, edge

            # equals is a special case, sometimes
            # an extra element may need to sneak in.
            if op is eq:
                if ranges[-1].leftedge == edge:
                    # the previous range also covered just this one slice.
                    ranges.pop()
            
                # equals is expressed as greater-than-equals and less-than-equals.
                ranges.append(Range(ge, edge, le, edge))
            
        if i == len(breaks) - 1:
            # get a left-boundary for the final range
            if op in (lt, ge):
                ranges.append(Range(ge, edge))
            else:
                ranges.append(Range(gt, edge))

    ranges = [range for range in ranges if range.isOpen()]
    
    # print breaks
    # print ranges
    
    if ranges:
        return ranges

    else:
        # if all else fails, return a Range that covers everything
        return [Range()]

def test_combinations(tests):
    """ Given a list of tests, return a list of possible combinations.
    """
    filters = []
    
    # quick hack to prevent memory overload
    if len(tests) > 15:
      max_test = 15
    else:
      max_test = len(tests)
    
    for i in range(int(math.pow(2, max_test))):
        filter = Filter()
    
        for (j, test) in enumerate(tests):
            if bool(i & (0x01 << j)):
                filter.tests.append(test)
            else:
                filter.tests.append(test.inverse())

        if filter.isOpen():
            filters.append(filter.minusExtras())

    return [filter.tests for filter in filters]

def xindexes(slots):
    """ Generate list of possible indexes into a list of slots.
    
        Best way to think of this is as a number where each digit might have a different radix.
        E.g.: (10, 10, 10) would return 10 x 10 x 10 = 1000 responses from (0, 0, 0) to (9, 9, 9),
        (2, 2, 2, 2) would return 2 x 2 x 2 x 2 = 16 responses from (0, 0, 0, 0) to (1, 1, 1, 1).
    """
    # the first response...
    slot = [0] * len(slots)
    
    for i in range(reduce(operator.mul, slots)):
        yield slot
        
        carry = 1
        
        # iterate from the least to the most significant digit
        for j in range(len(slots), 0, -1):
            k = j - 1
            
            slot[k] += carry
            
            if slot[k] >= slots[k]:
                carry = 1 + slot[k] - slots[k]
                slot[k] = 0
            else:
                carry = 0

def selectors_filters(selectors):
    """ Given a list of selectors and a map, return a list of Filters that
        fully describes all possible unique equality tests within those selectors.
    """
    tests = {}
    arg1s = set()
    
    # get all the tests and test.arg1 values out of the selectors
    for selector in selectors:
        for test in selector.allTests():
            if test.isSimple():
                tests[str(test)] = test
                arg1s.add(test.arg1)

    arg1s = sorted(list(arg1s))
    tests = tests.values()
    filters = []
    arg1tests = {}
    
    if len(tests):
        # divide up the tests by their first argument, e.g. "landuse" vs. "tourism",
        # into lists of all possible legal combinations of those tests.
        for arg1 in arg1s:
            arg1tests[arg1] = test_combinations([test for test in tests if test.arg1 == arg1])
            
        # get a list of the number of combinations for each group of tests from above.
        arg1counts = [len(arg1tests[arg1]) for arg1 in arg1s]
        
        # now iterate over each combination - for large numbers of tests, this can get big really, really fast
        for arg1indexes in xindexes(arg1counts):
            # list of lists of tests
            testslist = [arg1tests[arg1s[i]][j] for (i, j) in enumerate(arg1indexes)]
            
            # corresponding filter
            filter = Filter(*reduce(operator.add, testslist))
            
            filters.append(filter)
    
        if len(filters):
            return filters

    # if no filters have been defined, return a blank one that matches anything
    return [Filter()]

def next_counter():
    global counter
    counter += 1
    return counter

def is_gym_projection(map_el):
    """ Return true if the map projection matches that used by VEarth, Google, OSM, etc.
    
        Will be useful for a zoom-level shorthand for scale-denominator.
    """ 
    # expected
    gym = '+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null'
    gym = dict([p.split('=') for p in gym.split() if '=' in p])
    
    # observed
    srs = map_el.get('srs', '')
    srs = dict([p.split('=') for p in srs.split() if '=' in p])
    
    for p in gym:
        if srs.get(p, None) != gym.get(p, None):
            return False

    return True

def extract_declarations(map_el, base):
    """ Given a Map element and a URL base string, remove and return a complete
        list of style declarations from any Stylesheet elements found within.
    """
    declarations = []
    
    for stylesheet in map_el.findall('Stylesheet'):
        map_el.remove(stylesheet)
    
        if 'src' in stylesheet.attrib:
            url = urlparse.urljoin(base, stylesheet.attrib['src'])
            styles, local_base = urllib.urlopen(url).read(), url

        elif stylesheet.text:
            styles, local_base = stylesheet.text, base

        else:
            continue
            
        rulesets = style.parse_stylesheet(styles, base=local_base, is_gym=is_gym_projection(map_el))
        declarations += style.unroll_rulesets(rulesets)

    return declarations

def test2str(test):
    """ Return a mapnik-happy Filter expression atom for a single test
    """
    # for unquoting numbers
    unquoter = re.compile(r'^\'(\d+)\'$')
    
    if test.op == '!=':
        return "not [%s] = %s" % (test.arg1, unquoter.sub(r'\1', ("'%s'" % test.arg2)))
    elif test.op in ('<', '<=', '=', '>=', '>'):
        return "[%s] %s %s" % (test.arg1, test.op, unquoter.sub(r'\1', ("'%s'" % test.arg2)))
    else:
        raise Exception('"%s" is not a valid filter operation' % test.op)

def make_rule_element(range, filter, *symbolizer_els):
    """ Given a Range, return a Rule element prepopulated
        with applicable min/max scale denominator elements.
    """
    rule_el = Element('Rule')

    if range.leftedge:
        minscale = Element('MinScaleDenominator')
        rule_el.append(minscale)
    
        if range.leftop is ge:
            minscale.text = str(range.leftedge)
        elif range.leftop is gt:
            minscale.text = str(range.leftedge + 1)
    
    if range.rightedge:
        maxscale = Element('MaxScaleDenominator')
        rule_el.append(maxscale)
    
        if range.rightop is le:
            maxscale.text = str(range.rightedge)
        elif range.rightop is lt:
            maxscale.text = str(range.rightedge - 1)
    
    filter_text = ' and '.join(test2str(test) for test in filter.tests)
    
    if filter_text:
        filter_el = Element('Filter')
        filter_el.text = filter_text
        rule_el.append(filter_el)
    
    rule_el.tail = '\n        '
    
    for symbolizer_el in symbolizer_els:
        if symbolizer_el != False:
            rule_el.append(symbolizer_el)
    
    return rule_el

def insert_layer_style(map_el, layer_el, style_el):
    """ Given a Map element, a Layer element, and a Style element, insert the
        Style element into the flow and point to it from the Layer element.
    """
    style_el.tail = '\n    '
    map_el.insert(map_el._children.index(layer_el), style_el)
    
    stylename = Element('StyleName')
    stylename.text = style_el.get('name')
    stylename.tail = '\n        '
    layer_el.insert(layer_el._children.index(layer_el.find('Datasource')), stylename)
    layer_el.set('status', 'on')

def is_applicable_selector(selector, range, filter):
    """ Given a Selector, Range, and Filter, return True if the Selector is
        compatible with the given Range and Filter, and False if they contradict.
    """
    if not selector.inRange(range.midpoint()) and selector.isRanged():
        return False

    for test in selector.allTests():
        if not test.inFilter(filter.tests):
            return False
    
    return True

def add_map_style(map_el, declarations):
    """
    """
    property_map = {'map-bgcolor': 'bgcolor'}
    
    for dec in declarations:
        if dec.property.name in property_map:
            map_el.set(property_map[dec.property.name], str(dec.value))

def ranged_filtered_property_declarations(declarations, property_map):
    """ Given a list of declarations and a map of properties, return a list
        of rule tuples: (range, filter, parameter_values), where parameter_values
        is a list of (parameter, value) tuples.
    """
    # just the ones we care about here
    declarations = [dec for dec in declarations if dec.property.name in property_map]

    # a place to put rules
    rules = []
    
    # a matrix of checks for filter and min/max scale limitations
    ranges = selectors_ranges([dec.selector for dec in declarations])
    filters = selectors_filters([dec.selector for dec in declarations])
    
    for range in ranges:
        for filter in filters:
            rule = (range, filter, {})
            
            # collect all the applicable declarations into a list of parameters and values
            for dec in declarations:
                if is_applicable_selector(dec.selector, range, filter):
                    parameter = property_map[dec.property.name]
                    rule[2][parameter] = dec.value

            if rule[2]:
                rules.append(rule)

    return rules

def add_polygon_style(map_el, layer_el, declarations):
    """ Given a Map element, a Layer element, and a list of declarations,
        create a new Style element with a PolygonSymbolizer, add it to Map
        and refer to it in Layer.
    """
    property_map = {'polygon-fill': 'fill', 'polygon-opacity': 'fill-opacity'}
    
    # a place to put rule elements
    rule_els = []
    
    for (range, filter, parameter_values) in ranged_filtered_property_declarations(declarations, property_map):
        symbolizer_el = Element('PolygonSymbolizer')
        
        for (parameter, value) in parameter_values.items():
            parameter = Element('CssParameter', {'name': parameter})
            parameter.text = str(value)
            symbolizer_el.append(parameter)

        rule_el = make_rule_element(range, filter, symbolizer_el)
        rule_els.append(rule_el)
    
    if rule_els:
        style_el = Element('Style', {'name': 'polygon style %d' % next_counter()})
        style_el.text = '\n        '
        
        for rule_el in rule_els:
            style_el.append(rule_el)
        
        insert_layer_style(map_el, layer_el, style_el)

def add_line_style(map_el, layer_el, declarations):
    """ Given a Map element, a Layer element, and a list of declarations,
        create a new Style element with a LineSymbolizer, add it to Map
        and refer to it in Layer.
        
        This function is wise to both line-<foo> and outline-<foo> properties,
        and will generate pairs of LineSymbolizers if necessary.
    """
    property_map = {'line-color': 'stroke', 'line-width': 'stroke-width',
                    'line-opacity': 'stroke-opacity', 'line-join': 'stroke-linejoin',
                    'line-cap': 'stroke-linecap', 'line-dasharray': 'stroke-dasharray'}

    # temporarily prepend parameter names with 'in:' and 'out:' to be removed later
    for (property_name, parameter) in property_map.items():
        property_map['out' + property_name] = 'out:' + parameter
        property_map[property_name] = 'in:' + parameter
    
    # a place to put rule elements
    rule_els = []
    
    for (range, filter, parameter_values) in ranged_filtered_property_declarations(declarations, property_map):
        if 'in:stroke' in parameter_values and 'in:stroke-width' in parameter_values:
            insymbolizer_el = Element('LineSymbolizer')
        else:
            # we can do nothing with a weightless, colorless line
            continue
        
        if 'out:stroke' in parameter_values and 'out:stroke-width' in parameter_values:
            outsymbolizer_el = Element('LineSymbolizer')
        else:
            # we can do nothing with a weightless, colorless outline
            outsymbolizer_el = False
        
        for (parameter, value) in parameter_values.items():
            if parameter.startswith('in:'):
                # knock off the leading 'in:' from above
                parameter = Element('CssParameter', {'name': parameter[3:]})
                parameter.text = str(value)
                insymbolizer_el.append(parameter)

            elif parameter.startswith('out:') and outsymbolizer_el != False:
                # for the width...
                if parameter == 'out:stroke-width':
                    # ...double the weight and add the interior to make a proper outline
                    value = parameter_values['in:stroke-width'].value + 2 * value.value
            
                # knock off the leading 'out:' from above
                parameter = Element('CssParameter', {'name': parameter[4:]})
                parameter.text = str(value)
                outsymbolizer_el.append(parameter)

        rule_el = make_rule_element(range, filter, outsymbolizer_el, insymbolizer_el)
        rule_els.append(rule_el)
    
    if rule_els:
        style_el = Element('Style', {'name': 'line style %d' % next_counter()})
        style_el.text = '\n        '
        
        for rule_el in rule_els:
            style_el.append(rule_el)
        
        insert_layer_style(map_el, layer_el, style_el)

def add_text_styles(map_el, layer_el, declarations):
    """ Given a Map element, a Layer element, and a list of declarations,
        create new Style elements with a TextSymbolizer, add them to Map
        and refer to them in Layer.
    """
    property_map = {'text-face-name': 'face_name', 'text-size': 'size', 
                    'text-ratio': 'text_ratio', 'text-wrap-width': 'wrap_width', 'text-spacing': 'spacing',
                    'text-label-position-tolerance': 'label_position_tolerance',
                    'text-max-char-angle-delta': 'max_char_angle_delta', 'text-fill': 'fill',
                    'text-halo-fill': 'halo_fill', 'text-halo-radius': 'halo_radius',
                    'text-dx': 'dx', 'text-dy': 'dy',
                    'text-avoid-edges': 'avoid_edges', 'text-min-distance': 'min_distance',
                    'text-allow-overlap': 'allow_overlap', 'text-placement': 'placement'}

    # pull out all the names
    text_names = [dec.selector.elements[1].names[0]
                  for dec in declarations
                  if len(dec.selector.elements) is 2 and len(dec.selector.elements[1].names) is 1]

    # a separate style element for each text name
    for text_name in set(text_names):
    
        # just the ones we care about here.
        # the complicated conditional means: get all declarations that
        # apply to this text_name specifically, or text in general.
        name_declarations = [dec for dec in declarations
                             if dec.property.name in property_map
                                and (len(dec.selector.elements) == 1
                                     or (len(dec.selector.elements) == 2
                                         and dec.selector.elements[1].names[0] in (text_name, '*')))]
        
        # a place to put rule elements
        rule_els = []
        
        for (range, filter, parameter_values) in ranged_filtered_property_declarations(name_declarations, property_map):
            if 'face_name' in parameter_values and 'size' in parameter_values:
                symbolizer_el = Element('TextSymbolizer')
            else:
                # we can do nothing with fontless text
                continue

            symbolizer_el.set('name', text_name)
            
            for (parameter, value) in parameter_values.items():
                symbolizer_el.set(parameter, str(value))
    
            rule_el = make_rule_element(range, filter, symbolizer_el)
            rule_els.append(rule_el)
        
        if rule_els:
            style_el = Element('Style', {'name': 'text style %d (%s)' % (next_counter(), text_name)})
            style_el.text = '\n        '
            
            for rule_el in rule_els:
                style_el.append(rule_el)
            
            insert_layer_style(map_el, layer_el, style_el)

def postprocess_symbolizer_image_file(symbolizer_el, out, temp_name):
    """ Given a sumbolizer element, output directory name, and temporary
        file name, find the "file" attribute in the symbolizer and save it
        to a temporary location as a PING while noting its dimensions.
    """
    # read the image to get some more details
    img_path = symbolizer_el.get('file')
    img_data = urllib.urlopen(img_path).read()
    img_file = StringIO.StringIO(img_data)
    img = PIL.Image.open(img_file)
    
    # save the image to a tempfile, making it a PNG no matter what
    (handle, path) = tempfile.mkstemp('.png', 'cascadenik-%s-' % temp_name, out)
    os.close(handle)
    
    img.save(path)
    os.chmod(path, 0644);

    symbolizer_el.set('file', path)
    symbolizer_el.set('type', 'png')
    
    # if no width/height have been provided, set them
    if not (symbolizer_el.get('width', False) and symbolizer_el.get('height', False)):
        symbolizer_el.set('width', str(img.size[0]))
        symbolizer_el.set('height', str(img.size[1]))

def add_shield_styles(map_el, layer_el, declarations, out=None):
    """ Given a Map element, a Layer element, and a list of declarations,
        create new Style elements with a TextSymbolizer, add them to Map
        and refer to them in Layer.
    """
    property_map = {'shield-face-name': 'face_name', 'shield-size': 'size', 
                    'shield-fill': 'fill', 'shield-min-distance': 'min_distance',
                    'shield-file': 'file', 'shield-width': 'width', 'shield-height': 'height' }

    # pull out all the names
    text_names = [dec.selector.elements[1].names[0]
                  for dec in declarations
                  if len(dec.selector.elements) is 2 and len(dec.selector.elements[1].names) is 1]

    # a separate style element for each text name
    for text_name in set(text_names):
    
        # just the ones we care about here.
        # the complicated conditional means: get all declarations that
        # apply to this text_name specifically, or text in general.
        name_declarations = [dec for dec in declarations
                             if dec.property.name in property_map
                                and (len(dec.selector.elements) == 1
                                     or (len(dec.selector.elements) == 2
                                         and dec.selector.elements[1].names[0] in (text_name, '*')))]
        
        # a place to put rule elements
        rule_els = []
        
        for (range, filter, parameter_values) in ranged_filtered_property_declarations(name_declarations, property_map):
            if 'file' in parameter_values and 'face_name' in parameter_values and 'size' in parameter_values:
                symbolizer_el = Element('ShieldSymbolizer')
            else:
                # we can do nothing with fontless text
                continue

            symbolizer_el.set('name', text_name)
            
            for (parameter, value) in parameter_values.items():
                symbolizer_el.set(parameter, str(value))
    
            if symbolizer_el.get('file', False):
                postprocess_symbolizer_image_file(symbolizer_el, out, 'shield')
    
                rule_el = make_rule_element(range, filter, symbolizer_el)
                rule_els.append(rule_el)
        
        if rule_els:
            style_el = Element('Style', {'name': 'shield style %d (%s)' % (next_counter(), text_name)})
            style_el.text = '\n        '
            
            for rule_el in rule_els:
                style_el.append(rule_el)
            
            insert_layer_style(map_el, layer_el, style_el)

def add_point_style(map_el, layer_el, declarations, out=None):
    """ Given a Map element, a Layer element, and a list of declarations,
        create a new Style element with a PointSymbolizer, add it to Map
        and refer to it in Layer.
        
        Optionally provide an output directory for local copies of image files.
    """
    property_map = {'point-file': 'file', 'point-width': 'width',
                    'point-height': 'height', 'point-type': 'type',
                    'point-allow-overlap': 'allow_overlap'}
    
    # a place to put rule elements
    rule_els = []
    
    for (range, filter, parameter_values) in ranged_filtered_property_declarations(declarations, property_map):
        symbolizer_el = Element('PointSymbolizer')
        
        # collect all the applicable declarations into a symbolizer element
        for (parameter, value) in parameter_values.items():
            symbolizer_el.set(parameter, str(value))
    
        if symbolizer_el.get('file', False):
            postprocess_symbolizer_image_file(symbolizer_el, out, 'point')
            
            rule_el = make_rule_element(range, filter, symbolizer_el)
            rule_els.append(rule_el)
    
    if rule_els:
        style_el = Element('Style', {'name': 'point style %d' % next_counter()})
        style_el.text = '\n        '
        
        for rule_el in rule_els:
            style_el.append(rule_el)
        
        insert_layer_style(map_el, layer_el, style_el)

def add_polygon_pattern_style(map_el, layer_el, declarations, out=None):
    """ Given a Map element, a Layer element, and a list of declarations,
        create a new Style element with a PolygonPatternSymbolizer, add it to Map
        and refer to it in Layer.
        
        Optionally provide an output directory for local copies of image files.
    """
    property_map = {'polygon-pattern-file': 'file', 'polygon-pattern-width': 'width',
                    'polygon-pattern-height': 'height', 'polygon-pattern-type': 'type'}
    
    # a place to put rule elements
    rule_els = []
    
    for (range, filter, parameter_values) in ranged_filtered_property_declarations(declarations, property_map):
        symbolizer_el = Element('PolygonPatternSymbolizer')
        
        # collect all the applicable declarations into a symbolizer element
        for (parameter, value) in parameter_values.items():
            symbolizer_el.set(parameter, str(value))
    
        if symbolizer_el.get('file', False):
            postprocess_symbolizer_image_file(symbolizer_el, out, 'polygon-pattern')
            
            rule_el = make_rule_element(range, filter, symbolizer_el)
            rule_els.append(rule_el)
    
    if rule_els:
        style_el = Element('Style', {'name': 'polygon pattern style %d' % next_counter()})
        style_el.text = '\n        '
        
        for rule_el in rule_els:
            style_el.append(rule_el)
        
        insert_layer_style(map_el, layer_el, style_el)

def add_line_pattern_style(map_el, layer_el, declarations, out=None):
    """ Given a Map element, a Layer element, and a list of declarations,
        create a new Style element with a LinePatternSymbolizer, add it to Map
        and refer to it in Layer.
        
        Optionally provide an output directory for local copies of image files.
    """
    property_map = {'line-pattern-file': 'file', 'line-pattern-width': 'width',
                    'line-pattern-height': 'height', 'line-pattern-type': 'type'}
    
    # a place to put rule elements
    rule_els = []
    
    for (range, filter, parameter_values) in ranged_filtered_property_declarations(declarations, property_map):
        symbolizer_el = Element('LinePatternSymbolizer')
        
        # collect all the applicable declarations into a symbolizer element
        for (parameter, value) in parameter_values.items():
            symbolizer_el.set(parameter, str(value))
    
        if symbolizer_el.get('file', False):
            postprocess_symbolizer_image_file(symbolizer_el, out, 'line-pattern')
            
            rule_el = make_rule_element(range, filter, symbolizer_el)
            rule_els.append(rule_el)
    
    if rule_els:
        style_el = Element('Style', {'name': 'line pattern style %d' % next_counter()})
        style_el.text = '\n        '
        
        for rule_el in rule_els:
            style_el.append(rule_el)
        
        insert_layer_style(map_el, layer_el, style_el)

def get_applicable_declarations(element, declarations):
    """ Given an XML element and a list of declarations, return the ones
        that match as a list of (property, value, selector) tuples.
    """
    element_tag = element.tag
    element_id = element.get('id', None)
    element_classes = element.get('class', '').split()

    return [dec for dec in declarations
            if dec.selector.matches(element_tag, element_id, element_classes)]

def compile(src, dir=None):
    """
    """
    doc = xml.etree.ElementTree.parse(urllib.urlopen(src))
    map = doc.getroot()
    
    declarations = extract_declarations(map, src)
    
    add_map_style(map, get_applicable_declarations(map, declarations))

    for layer in map.findall('Layer'):
    
        for parameter in layer.find('Datasource').findall('Parameter'):
            if parameter.get('name', None) == 'file':
                # make shapefiles absolute paths
                parameter.text = os.path.realpath(urlparse.urljoin(src, parameter.text))

            elif parameter.get('name', None) == 'table':
                # remove line breaks from possible SQL
                parameter.text = parameter.text.replace('\r', ' ').replace('\n', ' ')

        if layer.get('status') == 'off':
            # don't bother
            continue
    
        # the default...
        layer.set('status', 'off')

        layer_declarations = get_applicable_declarations(layer, declarations)
        
        #pprint.PrettyPrinter().pprint(layer_declarations)
        
        add_polygon_style(map, layer, layer_declarations)
        add_polygon_pattern_style(map, layer, layer_declarations, dir)
        add_line_style(map, layer, layer_declarations)
        add_line_pattern_style(map, layer, layer_declarations, dir)
        add_shield_styles(map, layer, layer_declarations, dir)
        add_text_styles(map, layer, layer_declarations)
        add_point_style(map, layer, layer_declarations, dir)
        
        layer.set('name', 'layer %d' % next_counter())
        
        if 'id' in layer.attrib:
            del layer.attrib['id']
    
        if 'class' in layer.attrib:
            del layer.attrib['class']

    out = StringIO.StringIO()
    doc.write(out)
    
    return out.getvalue()
