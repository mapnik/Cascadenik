import os, sys
import math
import urllib
import urlparse
import tempfile
import StringIO
import operator
from operator import lt, le, eq, ge, gt
import base64
import os.path
import zipfile
import shutil

# cascadenik
import safe64
import style

HAS_PIL = False
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    try:
        import Image
        HAS_PIL = True
    except ImportError:
        pass

if not HAS_PIL:
    warn = 'Warning: PIL (Python Imaging Library) is required for proper handling of image symbolizers when using JPEG format images or not running Mapnik >=0.7.0\n'
    sys.stderr.write(warn)

DEFAULT_ENCODING = 'utf-8'

SHAPE_PARTS = (('.shp', True), ('.shx', True), ('.dbf', True), ('.prj', False), ('.index', False))

try:
    import lxml.etree as ElementTree
    from lxml.etree import Element
except ImportError:
    try:
        import xml.etree.ElementTree as ElementTree
        from xml.etree.ElementTree import Element
    except ImportError:
        import elementtree.ElementTree as ElementTree
        from elementtree.ElementTree import Element

opsort = {lt: 1, le: 2, eq: 3, ge: 4, gt: 5}
opstr = {lt: '<', le: '<=', eq: '==', ge: '>=', gt: '>'}


VERBOSE = False

def msg(msg):
    if VERBOSE:
        sys.stderr.write('Cascadenik debug: %s\n' % msg)

counter = 0

def next_counter():
    global counter
    counter += 1
    return counter

def url2fs(url):
    """ encode a URL to be safe as a filename """
    uri, extension = os.path.splitext(url)
    return safe64.dir(uri) + extension

def fs2url(url):
    """ decode a filename to the URL it is derived from """
    return safe64.decode(url)

def indent(elem, level=0):
    """ http://infix.se/2007/02/06/gentlemen-indent-your-xml
    """
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for e in elem:
            indent(e, level+1)
            if not e.tail or not e.tail.strip():
                e.tail = i + "  "
        if not e.tail or not e.tail.strip():
            e.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

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
    
    def toFilter(self, property):
        """ Convert this range to a Filter with a tests having a given property.
        """
        if self.leftedge == self.rightedge and self.leftop is ge and self.rightop is le:
            # equivalent to ==
            return Filter(style.SelectorAttributeTest(property, '=', self.leftedge))
    
        try:
            return Filter(style.SelectorAttributeTest(property, opstr[self.leftop], self.leftedge),
                          style.SelectorAttributeTest(property, opstr[self.rightop], self.rightedge))
        except KeyError:
            try:
                return Filter(style.SelectorAttributeTest(property, opstr[self.rightop], self.rightedge))
            except KeyError:
                try:
                    return Filter(style.SelectorAttributeTest(property, opstr[self.leftop], self.leftedge))
                except KeyError:
                    return Filter()
    
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
                if equals.has_key(test.property) and test.value != equals[test.property]:
                    # we've already stated that this arg must equal something else
                    return False
                    
                if nequals.has_key(test.property) and test.value in nequals[test.property]:
                    # we've already stated that this arg must not equal its current value
                    return False
                    
                equals[test.property] = test.value
        
            if test.op == '!=':
                if equals.has_key(test.property) and test.value == equals[test.property]:
                    # we've already stated that this arg must equal its current value
                    return False
                    
                if not nequals.has_key(test.property):
                    nequals[test.property] = set()

                nequals[test.property].add(test.value)
        
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
                equals[test.property] = test.value

        extras = []

        for (i, test) in enumerate(trimmed.tests):
            if test.op == '!=' and equals.has_key(test.property) and equals[test.property] != test.value:
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
        # get the scale tests to the front of the line, followed by regular alphabetical
        key_func = lambda t: (not t.isMapScaled(), t.property, t.op, t.value)

        # extract tests into cleanly-sortable tuples
        self_tuples = [(t.property, t.op, t.value) for t in sorted(self.tests, key=key_func)]
        other_tuples = [(t.property, t.op, t.value) for t in sorted(other.tests, key=key_func)]
        
        return cmp(self_tuples, other_tuples)

def test_ranges(tests):
    """ Given a list of tests, return a list of Ranges that fully describes
        all possible unique ranged slices within those tests.
        
        This function was hard to write, it should be hard to read.
        
        TODO: make this work for <= following by >= in breaks
    """
    if len(tests) == 0:
        return [Range()]
    
    assert 1 == len(set(test.property for test in tests)), 'All tests must share the same property'
    assert True in [test.isRanged() for test in tests], 'At least one test must be ranged'
    assert False not in [test.isNumeric() for test in tests], 'All tests must be numeric'
    
    repeated_breaks = []
    
    # start by getting all the range edges from the selectors into a list of break points
    for test in tests:
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
            elif op is ge:
                ranges.append(Range(None, None, lt, edge))
            elif op is gt:
                ranges.append(Range(None, None, le, edge))
            elif op is eq:
                # edge case
                ranges.append(Range(None, None, lt, edge))
                ranges.append(Range(ge, edge, le, edge))

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

def test_combinations(tests, filter=None):
    """ Given a list of simple =/!= tests, return a list of possible combinations.
    
        The filter argument is used to call test_combinations() recursively;
        this cuts down on the potential tests^2 number of combinations by
        identifying closed filters early and culling them from consideration.
    """
    # is the first one simple? it should be
    if len(tests) >= 1:
        assert tests[0].isSimple(), 'All tests must be simple, i.e. = or !='
    
    # does it share a property with the next one? it should
    if len(tests) >= 2:
        assert tests[0].property == tests[1].property, 'All tests must share the same property'

    # -------- remaining tests will be checked in subsequent calls --------
    
    # bail early
    if len(tests) == 0:
        return []

    # base case where no filter has been passed
    if filter is None:
        filter = Filter()

    # knock one off the front
    first_test, remaining_tests = tests[0], tests[1:]
    
    # one filter with the front test on it
    this_filter = filter.clone()
    this_filter.tests.append(first_test)
    
    # another filter with the inverse of the front test on it
    that_filter = filter.clone()
    that_filter.tests.append(first_test.inverse())
    
    # return value
    test_sets = []
    
    for new_filter in (this_filter, that_filter):
        if new_filter.isOpen():
            if len(remaining_tests) > 0:
                # keep diving deeper
                test_sets += test_combinations(remaining_tests, new_filter)
            
            else:
                # only append once the list has been exhausted
                new_set = []
                
                for test in new_filter.minusExtras().tests:
                    if test not in new_set:
                        new_set.append(test)
    
                test_sets.append(new_set)

    return test_sets

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

def selectors_tests(selectors, property=None):
    """ Given a list of selectors, return a list of unique tests.
    
        Optionally limit to those with a given property.
    """
    tests = {}
    
    for selector in selectors:
        for test in selector.allTests():
            if property is None or test.property == property:
                tests[unicode(test)] = test

    return tests.values()

def tests_filter_combinations(tests):
    """ Return a complete list of filter combinations for given list of tests
    """
    if len(tests) == 0:
        return [Filter()]
    
    # unique properties
    properties = sorted(list(set([test.property for test in tests])))

    property_tests = {}
    
    # divide up the tests by their first argument, e.g. "landuse" vs. "tourism",
    # into lists of all possible legal combinations of those tests.
    for property in properties:
        
        # limit tests to those with the current property
        current_tests = [test for test in tests if test.property == property]
        
        has_ranged_tests = True in [test.isRanged() for test in current_tests]
        has_nonnumeric_tests = False in [test.isNumeric() for test in current_tests]
        
        if has_ranged_tests and has_nonnumeric_tests:
            raise Exception('Mixed ranged/non-numeric tests in %s' % str(current_tests))

        elif has_ranged_tests:
            property_tests[property] = [range.toFilter(property).tests for range in test_ranges(current_tests)]

        else:
            property_tests[property] = test_combinations(current_tests)
            
    # get a list of the number of combinations for each group of tests from above.
    property_counts = [len(property_tests[property]) for property in properties]
    
    filters = []
        
    # now iterate over each combination - for large numbers of tests, this can get big really, really fast
    for property_indexes in xindexes(property_counts):
        # list of lists of tests
        testslist = [property_tests[properties[i]][j] for (i, j) in enumerate(property_indexes)]
        
        # corresponding filter
        filter = Filter(*reduce(operator.add, testslist))
        
        filters.append(filter)

    if len(filters):
        return sorted(filters)

    # if no filters have been defined, return a blank one that matches anything
    return [Filter()]

def is_gym_projection(srs):
    """ Return true if the map projection matches that used by VEarth, Google, OSM, etc.
    
        Is currently necessary for zoom-level shorthand for scale-denominator.
    """
    if srs.lower() == '+init=epsg:900913':
        return True

    # observed
    srs = dict([p.split('=') for p in srs.split() if '=' in p])
    
    # expected
    # note, common optional modifiers like +no_defs, +over, and +wkt
    # are not pairs and should not prevent matching
    gym = '+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null'
    gym = dict([p.split('=') for p in gym.split() if '=' in p])
        
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
            styles, local_base = urllib.urlopen(url).read().decode(DEFAULT_ENCODING), url

        elif stylesheet.text:
            styles, local_base = stylesheet.text, base

        else:
            continue
        
        rulesets = style.stylesheet_rulesets(styles, base=local_base, is_gym=is_gym_projection(map_el.get('srs','')))
        declarations += style.rulesets_declarations(rulesets)

    return declarations

def test2str(test):
    """ Return a mapnik-happy Filter expression atom for a single test
    """
    if type(test.value) in (int, float):
        value = str(test.value)
    elif type(test.value) in (str, unicode):
        value = "'%s'" % test.value
    else:
        raise Exception("test2str doesn't know what to do with a %s" % type(test.value))
    
    if test.op == '!=':
        return "not [%s] = %s" % (test.property, value)
    elif test.op in ('<', '<=', '=', '>=', '>'):
        return "[%s] %s %s" % (test.property, test.op, value)
    else:
        raise Exception('"%s" is not a valid filter operation' % test.op)

def make_rule_element(filter, *symbolizer_els):
    """ Given a Filter, return a Rule element prepopulated with
        applicable min/max scale denominator and filter elements.
    """
    rule_el = Element('Rule')
    
    scale_tests = [test for test in filter.tests if test.isMapScaled()]
    other_tests = [test for test in filter.tests if not test.isMapScaled()]
    
    for scale_test in scale_tests:

        if scale_test.op in ('>', '>='):
            minscale = Element('MinScaleDenominator')
            rule_el.append(minscale)
        
            if scale_test.op == '>=':
                minscale.text = str(scale_test.value)
            elif scale_test.op == '>':
                minscale.text = str(scale_test.value + 1)

        if scale_test.op in ('<', '<='):
            maxscale = Element('MaxScaleDenominator')
            rule_el.append(maxscale)
        
            if scale_test.op == '<=':
                maxscale.text = str(scale_test.value)
            elif scale_test.op == '<':
                maxscale.text = str(scale_test.value - 1)
    
    filter_text = ' and '.join(test2str(test) for test in other_tests)
    
    if filter_text:
        filter_el = Element('Filter')
        filter_el.text = filter_text
        rule_el.append(filter_el)
    
    rule_el.tail = '\n        '
    
    for symbolizer_el in symbolizer_els:
        if symbolizer_el != False:
            rule_el.append(symbolizer_el)
    
    return rule_el

def insert_layer_style(map_el, layer_el, style_name, rule_els):
    """ Given a Map element, a Layer element, a style name and a list of Rule
        elements, create a new Style element and insert it into the flow and
        point to it from the Layer element.
    """
    if not rule_els:
        return
    
    style_el = Element('Style', {'name': style_name})
    style_el.text = '\n        '
    
    for rule_el in rule_els:
        style_el.append(rule_el)
    
    style_el.tail = '\n    '
    if hasattr(map_el,'getchildren'):
        map_el.insert(map_el.getchildren().index(layer_el), style_el)
    else:
        map_el.insert(map_el._children.index(layer_el), style_el)
    
    stylename_el = Element('StyleName')
    stylename_el.text = style_name
    stylename_el.tail = '\n        '

    if hasattr(map_el,'getchildren'):
        layer_el.insert(layer_el.getchildren().index(layer_el.find('Datasource')), stylename_el)
    else:
        layer_el.insert(layer_el._children.index(layer_el.find('Datasource')), stylename_el)
    
    layer_el.set('status', 'on')

def is_applicable_selector(selector, filter):
    """ Given a Selector and Filter, return True if the Selector is
        compatible with the given Filter, and False if they contradict.
    """
    for test in selector.allTests():
        if not test.isCompatible(filter.tests):
            return False
    
    return True

def add_map_style(map_el, declarations,**kwargs):
    """
    """

    if kwargs.get('mapnik_version') >= 800:
        property_map = {'map-bgcolor': 'background-color'}
    else:
        property_map = {'map-bgcolor': 'bgcolor'}    
    for dec in declarations:
        if dec.property.name in property_map:
            map_el.set(property_map[dec.property.name], str(dec.value))

def filtered_property_declarations(declarations, property_map):
    """
    """
    # just the ones we care about here
    declarations = [dec for dec in declarations if dec.property.name in property_map]
    selectors = [dec.selector for dec in declarations]

    # a place to put rules
    rules = []
    
    for filter in tests_filter_combinations(selectors_tests(selectors)):
        rule = (filter, {})
        
        # collect all the applicable declarations into a list of parameters and values
        for dec in declarations:
            if is_applicable_selector(dec.selector, filter):
                parameter = property_map[dec.property.name]
                rule[1][parameter] = dec.value

        if rule[1]:
            rules.append(rule)

    return rules

def get_polygon_rules(declarations,**kwargs):
    """ Given a Map element, a Layer element, and a list of declarations,
        create a new Style element with a PolygonSymbolizer, add it to Map
        and refer to it in Layer.
    """
    property_map = {'polygon-fill': 'fill', 'polygon-opacity': 'fill-opacity',
                    'polygon-gamma': 'gamma',
                    'polygon-meta-output': 'meta-output', 'polygon-meta-writer': 'meta-writer'}

    
    return apply_rules(declarations,'PolygonSymbolizer',property_map,**kwargs)


def apply_rules(declarations,elem_name,property_map,**kwargs):
    # a place to put rule elements
    rule_els = []
    
    for (filter, parameter_values) in filtered_property_declarations(declarations, property_map):
        symbolizer_el = Element(elem_name)
        
        for (parameter, value) in sorted(parameter_values.items()):
            if kwargs.get('mapnik_version') >= 800:
                symbolizer_el.set(parameter, str(value))
            else:
                parameter = Element('CssParameter', {'name': parameter})
                parameter.text = str(value)
                symbolizer_el.append(parameter)

        rule_el = make_rule_element(filter, symbolizer_el)
        rule_els.append(rule_el)
    
    return rule_els

def get_raster_rules(declarations,**kwargs):
    """ Given a Map element, a Layer element, and a list of declarations,
        create a new Style element with a PolygonSymbolizer, add it to Map
        and refer to it in Layer.
    """
    property_map = {'raster-opacity': 'opacity',
                    'raster-mode': 'mode',
                    'raster-scaling': 'scaling'
                    }

    return apply_rules(declarations,'RasterSymbolizer',property_map,**kwargs)

def get_marker_rules(declarations,**kwargs):
    """ Given a Map element, a Layer element, and a list of declarations,
        create a new Style element with a LineSymbolizer, add it to Map
        and refer to it in Layer.
        
        This function is wise to both line-<foo> and outline-<foo> properties,
        and will generate pairs of LineSymbolizers if necessary.
    """
    # basically not supported before Mapnik2
    if not kwargs.get('mapnik_version') >= 800:
        return
    
    property_map = {'marker-line-color': 'stroke', 'marker-line-width': 'stroke-width',
                    'marker-line-opacity': 'stroke-opacity', #'line-dasharray': 'stroke-dasharray',
                    'marker-fill': 'fill', 'marker-fill-opacity': 'opacity',
                    'marker-placement': 'placement','marker-type':'marker_type',
                    'marker-width':'width','marker-height':'height',
                    'marker-file':'file','marker-allow-overlap':'allow_overlap',
                    'marker-spacing':'spacing','marker-max-error':'max_error',
                    'marker-transform':'transform',
                    'marker-meta-output': 'meta-output', 'marker-meta-writer': 'meta-writer'}
    
    # a place to put rule elements
    rule_els = []
    
    for (filter, parameter_values) in filtered_property_declarations(declarations, property_map):
        symbolizer_el = Element('MarkersSymbolizer')

        for (parameter, value) in sorted(parameter_values.items()):
            symbolizer_el.set(parameter, str(value))

        rule_el = make_rule_element(filter, symbolizer_el)
        rule_els.append(rule_el)
    
    return rule_els

def get_line_rules(declarations,**kwargs):
    """ Given a Map element, a Layer element, and a list of declarations,
        create a new Style element with a LineSymbolizer, add it to Map
        and refer to it in Layer.
        
        This function is wise to both line-<foo> and outline-<foo> properties,
        and will generate pairs of LineSymbolizers if necessary.
    """
    property_map = {'line-color': 'stroke', 'line-width': 'stroke-width',
                    'line-opacity': 'stroke-opacity', 'line-join': 'stroke-linejoin',
                    'line-cap': 'stroke-linecap', 'line-dasharray': 'stroke-dasharray',
                    'line-meta-output': 'meta-output', 'line-meta-writer': 'meta-writer'}


    # temporarily prepend parameter names with 'in:', 'on:', and 'out:' to be removed later
    for (property_name, parameter) in property_map.items():
        property_map['in' + property_name] = 'in:' + parameter
        property_map['out' + property_name] = 'out:' + parameter
        property_map[property_name] = 'on:' + parameter
    
    # a place to put rule elements
    rule_els = []
    
    for (filter, parameter_values) in filtered_property_declarations(declarations, property_map):
        if 'on:stroke' in parameter_values and 'on:stroke-width' in parameter_values:
            line_symbolizer_el = Element('LineSymbolizer')
        else:
            # we can do nothing with a weightless, colorless line
            continue
        
        if 'out:stroke' in parameter_values and 'out:stroke-width' in parameter_values:
            outline_symbolizer_el = Element('LineSymbolizer')
        else:
            # we can do nothing with a weightless, colorless outline
            outline_symbolizer_el = False
        
        if 'in:stroke' in parameter_values and 'in:stroke-width' in parameter_values:
            inline_symbolizer_el = Element('LineSymbolizer')
        else:
            # we can do nothing with a weightless, colorless inline
            inline_symbolizer_el = False
        
        for (parameter, value) in sorted(parameter_values.items()):
            if parameter.startswith('on:'):
                # knock off the leading 'on:' from above
                if kwargs.get('mapnik_version') >= 800:
                    line_symbolizer_el.set(parameter[3:], str(value))
                else:
                    parameter = Element('CssParameter', {'name': parameter[3:]})
                    parameter.text = str(value)
                    line_symbolizer_el.append(parameter)

            elif parameter.startswith('in:') and inline_symbolizer_el != False:
                # knock off the leading 'in:' from above
                if kwargs.get('mapnik_version') >= 800:
                    inline_symbolizer_el.set(parameter[3:], str(value))
                else:
                    parameter = Element('CssParameter', {'name': parameter[3:]})
                    parameter.text = str(value)
                    inline_symbolizer_el.append(parameter)

            elif parameter.startswith('out:') and outline_symbolizer_el != False:
                # for the width...
                if parameter == 'out:stroke-width':
                    # ...double the weight and add the interior to make a proper outline
                    value = parameter_values['on:stroke-width'].value + 2 * value.value
            
                # knock off the leading 'out:' from above
                if kwargs.get('mapnik_version') >= 800:
                    outline_symbolizer_el.set(parameter[4:], str(value))
                else:
                    parameter = Element('CssParameter', {'name': parameter[4:]})
                    parameter.text = str(value)
                    outline_symbolizer_el.append(parameter)

        rule_el = make_rule_element(filter, outline_symbolizer_el, line_symbolizer_el, inline_symbolizer_el)
        rule_els.append(rule_el)
    
    return rule_els

def get_text_rule_groups(declarations):
    """ Given a Map element, a Layer element, and a list of declarations,
        create new Style elements with a TextSymbolizer, add them to Map
        and refer to them in Layer.
    """
    property_map = {'text-face-name': 'face_name', 'text-size': 'size', 
                    'text-ratio': 'text_ratio', 'text-wrap-width': 'wrap_width', 'text-spacing': 'spacing',
                    'text-label-position-tolerance': 'label_position_tolerance',
                    'text-max-char-angle-delta': 'max_char_angle_delta', 'text-fill': 'fill',
                    'text-halo-fill': 'halo_fill', 'text-halo-radius': 'halo_radius',
                    'text-dx': 'dx', 'text-dy': 'dy', 'text-character-spacing': 'character_spacing',
                    'text-line-spacing': 'line_spacing',
                    'text-avoid-edges': 'avoid_edges', 'text-min-distance': 'min_distance',
                    'text-allow-overlap': 'allow_overlap', 'text-placement': 'placement',
                    'text-meta-output': 'meta-output', 'text-meta-writer': 'meta-writer'}

    # pull out all the names
    text_names = [dec.selector.elements[1].names[0]
                  for dec in declarations
                  if len(dec.selector.elements) is 2 and len(dec.selector.elements[1].names) is 1]

    rule_el_groups = []
    
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
        
        for (filter, parameter_values) in filtered_property_declarations(name_declarations, property_map):
            if 'face_name' in parameter_values and 'size' in parameter_values:
                symbolizer_el = Element('TextSymbolizer')
            else:
                # we can do nothing with fontless text
                continue

            symbolizer_el.set('name', text_name)
            
            for (parameter, value) in parameter_values.items():
                symbolizer_el.set(parameter, str(value))
    
            rule_el = make_rule_element(filter, symbolizer_el)
            rule_els.append(rule_el)
        
        rule_el_groups.append((text_name, rule_els))

    return rule_el_groups

def postprocess_symbolizer_image_file(symbolizer_el, temp_name, **kwargs):
    """ Given a symbolizer element, output directory name, and temporary
        file name, find the "file" attribute in the symbolizer and save it
        to a target location as a PNG while noting its dimensions.
    """
    # read the image to get some more details
    img_path = symbolizer_el.get('file')

    msg('reading symbol: %s' % img_path)
    
    target_dir = kwargs.get('target_dir',tempfile.gettempdir())
    
    move_local_files = kwargs.get('move_local_files')

    # todo - use urlparse logic?
    is_local = os.path.exists(img_path)
    # if not url throw error?
    
    image_name, ext = os.path.splitext(img_path)

    # support latest mapnik features of auto-detection
    # of image sizes and jpeg reading support...
    ver = kwargs.get('mapnik_version',None)
    # http://trac.mapnik.org/ticket/508
    mapnik_auto_image_support = (ver >= 701) or (ver >= 700 and 'pattern' not in symbolizer_el.tag)
    mapnik_formats = ['.png','tif','tiff']
    if ver >= 800:
        mapnik_formats.extend(['.jpg','.jpeg'])
    supported_type = ext in mapnik_formats
    if supported_type:
        target_ext = ext
    else:
        target_ext = '.png'

    if move_local_files or not is_local:
        target_name = os.path.basename('%s%s' % (image_name,target_ext))
        if not is_local and kwargs.get('safe_urls'):
            # note we use/encode the raw url 'image_path' here...
            target_dir = os.path.join(target_dir,url2fs(img_path))
        dest_file = os.path.join(target_dir,target_name)
    else:
        # local file and we're not moving it
        dest_file = '%s%s' % (image_name,target_ext)

    msg('Destination file: %s' % dest_file)
        
    # are we caching, eg pulling from already downloaded files
    caching = not kwargs.get('no_cache')
    if not is_local and caching:
        if os.path.exists(dest_file):
            img_path = dest_file
            supported_type = os.path.splitext(img_path)[1] in mapnik_formats
            is_local = True
            msg('found locally cached file: %s' %  dest_file)

    # finally, early return if possible
    if is_local and os.path.exists(dest_file) and mapnik_auto_image_support and supported_type:
        symbolizer_el.set('file', dest_file)
        return
    
    # throw error if we need to detect image sizes and can't because pil is missing
    if not mapnik_auto_image_support and not HAS_PIL:
        raise SystemExit('PIL (Python Imaging Library) is required for handling image data unless you are using PNG inputs and running Mapnik >=0.7.0')

    # okay, we actually need read the data into memory now
    if is_local:
        img_data = open(img_path,'rb').read()
    else:
        #if os.path.isabs(img_path) and sys.platform == "win32":
        #    img_path = 'file:%s' % img_path
        img_data = urllib.urlopen(img_path).read()
    
    im = Image.open(StringIO.StringIO(img_data))

    if not mapnik_auto_image_support:
        # todo - providing widths has no effect as we don't resize
        #if not (symbolizer_el.get('width', False) and symbolizer_el.get('height', False)):
        symbolizer_el.set('width', str(im.size[0]))
        symbolizer_el.set('height', str(im.size[1]))
        symbolizer_el.set('type', target_ext[1:])

    if not os.path.exists(target_dir):
        os.mkdir(target_dir)

    im.save(dest_file)
    symbolizer_el.set('file', dest_file)
    os.chmod(dest_file, 0644)

    

def get_shield_rule_groups(declarations, **kwargs):
    """ Given a Map element, a Layer element, and a list of declarations,
        create new Style elements with a TextSymbolizer, add them to Map
        and refer to them in Layer.
    """
    property_map = {'shield-face-name': 'face_name', 'shield-size': 'size', 
                    'shield-fill': 'fill', 'shield-character-spacing': 'character_spacing',
                    'shield-line-spacing': 'line_spacing',
                    'shield-spacing': 'spacing', 'shield-min-distance': 'min_distance',
                    'shield-file': 'file', 'shield-width': 'width', 'shield-height': 'height',
                    'shield-meta-output': 'meta-output', 'shield-meta-writer': 'meta-writer'}

    # pull out all the names
    text_names = [dec.selector.elements[1].names[0]
                  for dec in declarations
                  if len(dec.selector.elements) is 2 and len(dec.selector.elements[1].names) is 1]

    rule_el_groups = []
    
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
        
        for (filter, parameter_values) in filtered_property_declarations(name_declarations, property_map):
            if 'file' in parameter_values and 'face_name' in parameter_values and 'size' in parameter_values:
                symbolizer_el = Element('ShieldSymbolizer')
            else:
                # we can do nothing with fontless text
                continue

            symbolizer_el.set('name', text_name)
            symbolizer_el.set('placement', 'line')
            
            for (parameter, value) in parameter_values.items():
                symbolizer_el.set(parameter, str(value))
    
            if symbolizer_el.get('file', False):
                postprocess_symbolizer_image_file(symbolizer_el, 'shield', **kwargs)
    
                rule_el = make_rule_element(filter, symbolizer_el)
                rule_els.append(rule_el)
        
        rule_el_groups.append((text_name, rule_els))

    return rule_el_groups

def get_point_rules(declarations, **kwargs):
    """ Given a Map element, a Layer element, and a list of declarations,
        create a new Style element with a PointSymbolizer, add it to Map
        and refer to it in Layer.
        
        Optionally provide an output directory for local copies of image files.
    """
    property_map = {'point-file': 'file', 'point-width': 'width',
                    'point-height': 'height', 'point-type': 'type',
                    'point-allow-overlap': 'allow_overlap',
                    'point-meta-output': 'meta-output', 'point-meta-writer': 'meta-writer'}
    
    # a place to put rule elements
    rule_els = []
    
    for (filter, parameter_values) in filtered_property_declarations(declarations, property_map):
        symbolizer_el = Element('PointSymbolizer')
        
        # collect all the applicable declarations into a symbolizer element
        for (parameter, value) in parameter_values.items():
            symbolizer_el.set(parameter, str(value))
    
        if symbolizer_el.get('file', False):
            postprocess_symbolizer_image_file(symbolizer_el, 'point', **kwargs)
            
            rule_el = make_rule_element(filter, symbolizer_el)
            rule_els.append(rule_el)
    
    return rule_els

def get_polygon_pattern_rules(declarations, **kwargs):
    """ Given a Map element, a Layer element, and a list of declarations,
        create a new Style element with a PolygonPatternSymbolizer, add it to Map
        and refer to it in Layer.
        
        Optionally provide an output directory for local copies of image files.
    """
    property_map = {'polygon-pattern-file': 'file', 'polygon-pattern-width': 'width',
                    'polygon-pattern-height': 'height', 'polygon-pattern-type': 'type',
                    'polygon-meta-output': 'meta-output', 'polygon-meta-writer': 'meta-writer'}

    
    # a place to put rule elements
    rule_els = []
    
    for (filter, parameter_values) in filtered_property_declarations(declarations, property_map):
        symbolizer_el = Element('PolygonPatternSymbolizer')
        
        # collect all the applicable declarations into a symbolizer element
        for (parameter, value) in parameter_values.items():
            symbolizer_el.set(parameter, str(value))
    
        if symbolizer_el.get('file', False):
            postprocess_symbolizer_image_file(symbolizer_el, 'polygon-pattern', **kwargs)
            
            rule_el = make_rule_element(filter, symbolizer_el)
            rule_els.append(rule_el)
    
    return rule_els

def get_line_pattern_rules(declarations, **kwargs):
    """ Given a Map element, a Layer element, and a list of declarations,
        create a new Style element with a LinePatternSymbolizer, add it to Map
        and refer to it in Layer.
        
        Optionally provide an output directory for local copies of image files.
    """
    property_map = {'line-pattern-file': 'file', 'line-pattern-width': 'width',
                    'line-pattern-height': 'height', 'line-pattern-type': 'type',
                    'line-pattern-meta-output': 'meta-output', 'line-pattern-meta-writer': 'meta-writer'}

    
    # a place to put rule elements
    rule_els = []
    
    for (filter, parameter_values) in filtered_property_declarations(declarations, property_map):
        symbolizer_el = Element('LinePatternSymbolizer')
        
        # collect all the applicable declarations into a symbolizer element
        for (parameter, value) in parameter_values.items():
            symbolizer_el.set(parameter, str(value))
    
        if symbolizer_el.get('file', False):
            postprocess_symbolizer_image_file(symbolizer_el, 'line-pattern', **kwargs)
            
            rule_el = make_rule_element(filter, symbolizer_el)
            rule_els.append(rule_el)
    
    return rule_els

def get_applicable_declarations(element, declarations):
    """ Given an XML element and a list of declarations, return the ones
        that match as a list of (property, value, selector) tuples.
    """
    element_tag = element.tag
    element_id = element.get('id', None)
    element_classes = element.get('class', '').split()

    return [dec for dec in declarations
            if dec.selector.matches(element_tag, element_id, element_classes)]


def handle_shapefile_parts(shapefile,target_dir):
    if not os.path.exists(target_dir):
        os.mkdir(target_dir)
    for (expected, required) in SHAPE_PARTS:
        if required and expected not in extensions:
            raise Exception('Shapefile %(shapefile)s missing extension "%(expected)s"' % locals())
        
        name = os.path.splitext(shapefile)[0]
        source = os.path.normpath('%(target_dir)s/%(basename)s' % locals())
        dest = os.path.normpath('%(target_dir)s/%(basename)s' % locals())
        
        shutil.copy()

def handle_zipped_shapefile(zipped_shp,target_dir):
    zip_data = urllib.urlopen(zipped_shp).read()
    zip_file = zipfile.ZipFile(StringIO.StringIO(zip_data))
    
    infos = zip_file.infolist()
    extensions = [os.path.splitext(info.filename)[1] for info in infos]
    basenames = [os.path.basename(info.filename) for info in infos]
    
    for (expected, required) in SHAPE_PARTS:
        if required and expected not in extensions:
            raise Exception('Zip file %(zipped_shp)s missing extension "%(expected)s"' % locals())

        for (info, extension, basename) in zip(infos, extensions, basenames):
            if extension == expected:
                file_data = zip_file.read(info.filename)
                if not os.path.exists(target_dir):
                    os.mkdir(target_dir)
                file_name = os.path.normpath('%(target_dir)s/%(basename)s' % locals())
                
                file_ = open(file_name, 'wb')
                file_.write(file_data)
                file_.close()
                
                if extension == '.shp':
                    local = file_name[:-4]
                
                break

    return local

def handle_placing_shapefile(shapefile,target_dir):
    if os.path.splitext(shapefile)[1] == '.zip':
        return handle_zipped_shapefile(shapefile,target_dir)
    else:
        return handle_shapefile_parts(shapefile,target_dir)

def localize_shapefile(src, shapefile, **kwargs):
    """ Given a stylesheet path, a shapefile name, and a temp directory,
        modify the shapefile name so it's an absolute path.
    
        Shapefile is assumed to be relative to the stylesheet path.
        If it's found to look like a URL (e.g. "http://...") it's assumed
        to be a remote zip file containing .shp, .shx, and .dbf files.
    """
    (scheme, netloc, path, params, query, fragment) = urlparse.urlparse(shapefile)

    move_local_files = kwargs.get('move_local_files')
    if move_local_files:
        sys.stderr.write('WARNING: moving local unzipped shapefiles not yet supported\n')

    if scheme == '':
        # assumed to be local
        if not os.path.splitext(shapefile)[1] == ".zip":
            # if not a local zip
            if kwargs.get('mapnik_version',None) >= 601:
                # Mapnik 0.6.1 accepts relative paths, so we leave it unchanged
                # but compiled file must maintain same relativity to the files
                # as the stylesheet, which needs to be addressed separately
                return shapefile
            else:
                msg('Warning, your Mapnik version is old and does not support relative paths to datasources')
                return os.path.realpath(urlparse.urljoin(src, shapefile))

    target_dir = kwargs.get('target_dir',tempfile.gettempdir())
    
    # if no-cache is True we avoid caching otherwise
    # we attempt to pull targets locally without re-downloading
    caching = not kwargs.get('no_cache',None)

    if kwargs.get('safe_urls'):
        #todo - make "safe64"
        target_dir = os.path.join(target_dir,url2fs(shapefile))
    
    if caching:
        if kwargs.get('safe_urls'):
            if not os.path.isdir(target_dir):
                # does not exist yet
                msg('Downloading shapefile to base64 encoded dir: %s' % target_dir)
            else:
                # already downloaded, we can pull shapefile name from cache
                msg('Shapefile found, pulling from base64 encoded directory cache instead of downloading')
                for root, dirs, files in os.walk(target_dir):
                    for file_ in files:
                        if os.path.splitext(file_)[1] == '.shp':
                            return os.path.join(root, file_[:-4])
        else:
            # only possibility here is to test assumption 
            # that the shapefile is the same name as the zip.
            basename = os.path.splitext(os.path.basename(shapefile))[0]
            possible_names = []
            possible_names.append(os.path.join(target_dir,'%s.shp' % basename))
            possible_names.append(os.path.join(target_dir,basename,'%s.shp' % basename))
            found = False
            unzipped_path = None
            for possible in possible_names:
                if os.path.exists(possible):
                    found = True
                    msg('Shapefile found locally, reading from "%s" instead of downloading' % possible)
                    unzipped_path = possible
                    break
            if not found:
                msg('Remote shapefile could not be found locally, therefore downloading from "%s"' % (shapefile))
                msg('(searched for %s)' %  possible_names)
            if unzipped_path:
                return unzipped_path
    else:
        msg('Avoiding searching for cached local files...')
        msg('Placing "%s" at "%s"' % (shapefile,target_dir))

    # assumed to be a remote zip archive with .shp, .shx, and .dbf files
    return handle_placing_shapefile(shapefile,target_dir)

def auto_detect_mapnik_version():
    mapnik = None
    try:
        import mapnik2 as mapnik
    except ImportError:
        try:
            import mapnik
        except ImportError:
            pass
    if mapnik:
        if hasattr(mapnik,'mapnik_version'):
            return mapnik.mapnik_version()

def mapnik_version_string(version):
    patch_level = version % 100
    minor_version = version / 100 % 1000
    major_version = version / 100000
    return '%s.%s.%s' % ( major_version, minor_version,patch_level)
            
def compile(src,**kwargs):
    """
    Compile a Cascadenik MML file, returning an XML string.
    
    Keyword Parameters:
         
     verbose:
       If True, debugging information will be printed to stderr. (default: None)
     
     srs:
       Target srs for the compiled stylesheet. If provided, overrides default map 
       srs in the mml.
       
     safe_urls:
       If True, paths of any files placed by Cascadenik will be base64 encoded calling
       safe64.url2fs() on the url or filesystem path.

     target_dir:
       If set, all file-based resources (symbols, shapefiles, etc) will be written to this
       output directory. If not set, tempfile.gettempdir() will be used.
     
     move_local_files:
       If True, not just remote files but also locally referenced files (currently only
       symbols) will be move to the 'target_dir'. Support for datasources will be added
       in the future. (default: None)
        
     no_cache:
       By default remotely downloaded files will be read from the location where they
       were unpacked ('target_dir'). If 'no_cache' is True, then remote files will be
       downloaded even if a local copy exists in the output location, effectively
       overwriting any previously downloaded remote files or moved local files.
     
     pretty:
       If True, XML output will be fully indented (otherwise indenting is haphazard).

     mapnik_version:
       The Mapnik release to target for optimal stylesheet compatibility.
       
       701 (aka '0.7.1') is the assumed default target, unless specified or autodetected.
              
       'mapnik_version' must be an integer matching the format of 
       include/mapnik/version.hpp which follows the Boost method:
       
         MAPNIK_VERSION % 100 is the sub-minor version
         MAPNIK_VERSION / 100 % 1000 is the minor version
         MAPNIK_VERSION / 100000 is the major version
       
       If not provided the mapnik_version will be autodetected by:
       
       >>> import mapnik
       >>> mapnik.mapnik_version()
       701
       
       This is equivalent to:
       
       >>> mapnik.mapnik_version_string()
       '0.7.1'
       
       To convert from the string to integer do:
       >>> n = mapnik.mapnik_version_string().split('.')
       >>> (int(n[0]) * 100000) + (int(n[1]) * 100) + (int(n[2]))
       701
       
    """

    global VERBOSE
    if kwargs.get('verbose'):
        VERBOSE = True
        sys.stderr.write('\n')
    
    if not kwargs.get('mapnik_version',None):
        msg('"mapnik_version" not provided, autodetecting...')
        version = auto_detect_mapnik_version()
        if version:
            kwargs['mapnik_version'] = version 
            msg('Autodetected Mapnik version: %s | %s' % (version,mapnik_version_string(version)))
        else:
            default_version = 701 # 0.7.1
            msg('Failed to autodetect "mapnik_version" falling back to %s | %s' % (default_version,mapnik_version_string(default_version)))
    else:
        msg('Targeting mapnik version: %s | %s' % (kwargs['mapnik_version'],mapnik_version_string(kwargs['mapnik_version'])))        
        
    if os.path.exists(src): # local file
        # using 'file:' enables support on win32
        # for opening local files with urllib.urlopen
        # Note: this must only be used with abs paths to local files
        # otherwise urllib will think they are absolute, 
        # therefore in the future it will likely be
        # wiser to just open local files with open()
        if os.path.isabs(src) and sys.platform == "win32":
            msg('prepending "file:" to %s for windows compatibility with urlopen and absolute paths' % src)
            src = 'file:%s' % src
    
    target_dir = kwargs.get('target_dir')
    if target_dir:
        msg('Writing all files to "target_dir": %s' % target_dir)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
            msg('"target_dir" does not exist, creating...')
    else:
        tmp_dir = tempfile.gettempdir()
        kwargs['target_dir'] = tmp_dir
        if kwargs.get('move_local_files'):
            msg('Writing all files to temporary directory: %s' % tmp_dir)
        else:       
            msg('Writing all remote files to temporary directory: %s' % tmp_dir)    

    doc = ElementTree.parse(urllib.urlopen(src))
    map_el = doc.getroot()
    
    # if a target srs is profiled, override whatever is in mml
    if kwargs.get('srs'):
        map_el.set('srs',kwargs.get('srs'))
    
    declarations = extract_declarations(map_el, src)
    
    add_map_style(map_el, get_applicable_declarations(map_el, declarations),**kwargs)

    for layer in map_el.findall('Layer'):
    
        ds_params = layer.find('Datasource').findall('Parameter')
        ds_type = [i.text for i in ds_params if i.get('name','') == 'type']
        if len(ds_type):
            ds_type = ds_type[0]
        
        for parameter in ds_params:
            # TODO - support other kinds of file-based datasources other than shapefiles
            if ds_type == 'shape' and parameter.get('name', None) == 'file':
                # fetch a remote, zipped shapefile or read a local one
                if parameter.text:
                    msg('Handling shapefile datasource...')
                    parameter.text = localize_shapefile(src, parameter.text, **kwargs)
                    # TODO - support datasource reprojection to make map srs
                    # TODO - support automatically indexing shapefiles
            elif ds_type == 'postgis' and parameter.get('name', None) == 'table':
                # remove line breaks from possible SQL
                # http://trac.mapnik.org/ticket/173
                if not kwargs.get('mapnik_version',None) >= 601:
                    parameter.text = parameter.text.replace('\r', ' ').replace('\n', ' ')
            elif parameter.get('name', None) == 'file':
                pass #msg('other file based datasource needing handling!')

        if layer.get('status') == 'off':
            # don't bother
            continue
    
        # the default...
        #layer.set('status', 'off')

        layer_declarations = get_applicable_declarations(layer, declarations)
                
        insert_layer_style(map_el, layer, 'polygon style %d' % next_counter(),
                           get_polygon_rules(layer_declarations,**kwargs) + \
                           get_polygon_pattern_rules(layer_declarations, **kwargs))
        
        insert_layer_style(map_el, layer, 'line style %d' % next_counter(),
                           get_line_rules(layer_declarations,**kwargs) + \
                           get_line_pattern_rules(layer_declarations, **kwargs))

        insert_layer_style(map_el, layer, 'marker style %d' % next_counter(),
                           get_marker_rules(layer_declarations,**kwargs))

        insert_layer_style(map_el, layer, 'raster style %d' % next_counter(),
                           get_raster_rules(layer_declarations,**kwargs))

        for (shield_name, shield_rule_els) in get_shield_rule_groups(layer_declarations, **kwargs):
            insert_layer_style(map_el, layer, 'shield style %d (%s)' % (next_counter(), shield_name), shield_rule_els)

        for (text_name, text_rule_els) in get_text_rule_groups(layer_declarations):
            insert_layer_style(map_el, layer, 'text style %d (%s)' % (next_counter(), text_name), text_rule_els)

        insert_layer_style(map_el, layer, 'point style %d' % next_counter(), \
            get_point_rules(layer_declarations, **kwargs))
        
        layer.set('name', 'layer %d' % next_counter())
        
        if 'id' in layer.attrib:
            del layer.attrib['id']
    
        if 'class' in layer.attrib:
            del layer.attrib['class']

    if kwargs.get('pretty',None):
        indent(map_el)
    
    xml_out = StringIO.StringIO()
    doc.write(xml_out)
    
    return xml_out.getvalue()
