import os, sys
import math
import urllib
import urllib2
import urlparse
import tempfile
import StringIO
import operator
from operator import lt, le, eq, ge, gt
import base64
import os.path
import zipfile
import style, output
import shutil

# cascadenik
import safe64
import style

try:
    from PIL import Image
except ImportError:
    try:
        import Image
    except ImportError:
        Image = False

if not Image:
    warn = 'Warning: PIL (Python Imaging Library) is required for proper handling of image symbolizers when using JPEG format images or not running Mapnik >=0.7.0\n'
    sys.stderr.write(warn)

DEFAULT_ENCODING = 'utf-8'

SHAPE_PARTS = (('.shp', True), ('.shx', True), ('.dbf', True), ('.prj', False), ('.index', False))

try:
    import xml.etree.ElementTree as ElementTree
    from xml.etree.ElementTree import Element
except ImportError:
    try:
        import lxml.etree as ElementTree
        from lxml.etree import Element
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

def make_rule(filter, *symbolizers):
    """ Given a Filter and some symbolizers, return a Rule prepopulated
        with applicable min/max scale denominator and filter.
    """
    scale_tests = [test for test in filter.tests if test.isMapScaled()]
    other_tests = [test for test in filter.tests if not test.isMapScaled()]
    
    # these will be replaced with values as necessary
    minscale, maxscale, filter = None, None, None
    
    for scale_test in scale_tests:

        if scale_test.op in ('>', '>='):
            if scale_test.op == '>=':
                value = scale_test.value
            elif scale_test.op == '>':
                value = scale_test.value + 1

            minscale = output.MinScaleDenominator(value)

        if scale_test.op in ('<', '<='):
            if scale_test.op == '<=':
                value = scale_test.value
            elif scale_test.op == '<':
                value = scale_test.value - 1

            maxscale = output.MaxScaleDenominator(value)
    
    filter_text = ' and '.join(test2str(test) for test in other_tests)
    
    if filter_text:
        filter = output.Filter(filter_text)

    rule = output.Rule(minscale, maxscale, filter, [s for s in symbolizers if s])
    
    return rule

def is_applicable_selector(selector, filter):
    """ Given a Selector and Filter, return True if the Selector is
        compatible with the given Filter, and False if they contradict.
    """
    for test in selector.allTests():
        if not test.isCompatible(filter.tests):
            return False
    
    return True

def get_map_attributes(declarations, **kwargs):
    """
    """
    property_map = {'map-bgcolor': 'bgcolor'}    
    
    return dict([(property_map[dec.property.name], dec.value.value)
                 for dec in declarations
                 if dec.property.name in property_map])

def filtered_property_declarations(declarations, property_names):
    """
    """
    # just the ones we care about here
    declarations = [dec for dec in declarations if dec.property.name in property_names]
    selectors = [dec.selector for dec in declarations]

    # a place to put rules
    rules = []
    
    for filter in tests_filter_combinations(selectors_tests(selectors)):
        rule = {}
        
        # collect all the applicable declarations into a list of parameters and values
        for dec in declarations:
            if is_applicable_selector(dec.selector, filter):
                rule[dec.property.name] = dec.value

        if rule:
            rules.append((filter, rule))

    return rules

def get_polygon_rules(declarations,**kwargs):
    """ Given a Map element, a Layer element, and a list of declarations,
        create a new Style element with a PolygonSymbolizer, add it to Map
        and refer to it in Layer.
    """
    property_map = {'polygon-fill': 'fill', 'polygon-opacity': 'fill-opacity',
                    'polygon-gamma': 'gamma',
                    'polygon-meta-output': 'meta-output', 'polygon-meta-writer': 'meta-writer'}

    property_names = property_map.keys()
    
    # a place to put rules
    rules = []
    
    for (filter, values) in filtered_property_declarations(declarations, property_names):
        color = values.has_key('polygon-fill') and values['polygon-fill'].value
        opacity = values.has_key('polygon-opacity') and values['polygon-opacity'].value or None
        gamma = values.has_key('polygon-gamma') and values['polygon-gamma'].value or None
        symbolizer = color and output.PolygonSymbolizer(color, opacity, gamma)
        
        if symbolizer:
            rules.append(make_rule(filter, symbolizer))
    
    return rules

def get_raster_rules(declarations,**kwargs):
    """ Given a Map element, a Layer element, and a list of declarations,
        create a new Style element with a RasterSymbolizer, add it to Map
        and refer to it in Layer.
    """
    property_map = {'raster-opacity': 'opacity',
                    'raster-mode': 'mode',
                    'raster-scaling': 'scaling'
                    }

    property_names = property_map.keys()

    # a place to put rules
    rules = []

    for (filter, values) in filtered_property_declarations(declarations, property_names):
        sym_params = {}
        for prop,attr in property_map.items():
            sym_params[attr] = values.has_key(prop) and values[prop].value or None
        
        symbolizer = output.RasterSymbolizer(**sym_params)

        rules.append(make_rule(filter, symbolizer))

    return rules

def get_line_rules(declarations, **kwargs):
    """ Given a list of declarations, return a list of output.Rule objects.
        
        This function is wise to line-<foo>, inline-<foo>, and outline-<foo> properties,
        and will generate multiple LineSymbolizers if necessary.
    """
    property_map = {'line-color': 'stroke', 'line-width': 'stroke-width',
                    'line-opacity': 'stroke-opacity', 'line-join': 'stroke-linejoin',
                    'line-cap': 'stroke-linecap', 'line-dasharray': 'stroke-dasharray',
                    'line-meta-output': 'meta-output', 'line-meta-writer': 'meta-writer'}


    property_names = property_map.keys()
    
    # prepend parameter names with 'in' and 'out'
    for i in range(len(property_names)):
        property_names.append('in' + property_names[i])
        property_names.append('out' + property_names[i])

    # a place to put rules
    rules = []
    
    for (filter, values) in filtered_property_declarations(declarations, property_names):
    
        width = values.has_key('line-width') and values['line-width'].value
        color = values.has_key('line-color') and values['line-color'].value

        opacity = values.has_key('line-opacity') and values['line-opacity'].value or None
        join = values.has_key('line-join') and values['line-join'].value or None
        cap = values.has_key('line-cap') and values['line-cap'].value or None
        dashes = values.has_key('line-dasharray') and values['line-dasharray'].value or None

        line_symbolizer = color and width and output.LineSymbolizer(color, width, opacity, join, cap, dashes) or False

        width = values.has_key('inline-width') and values['inline-width'].value
        color = values.has_key('inline-color') and values['inline-color'].value

        opacity = values.has_key('inline-opacity') and values['inline-opacity'].value or None
        join = values.has_key('inline-join') and values['inline-join'].value or None
        cap = values.has_key('inline-cap') and values['inline-cap'].value or None
        dashes = values.has_key('inline-dasharray') and values['inline-dasharray'].value or None

        inline_symbolizer = color and width and output.LineSymbolizer(color, width, opacity, join, cap, dashes) or False

        # outline requires regular line to have a meaningful width
        width = values.has_key('outline-width') and values.has_key('line-width') \
            and values['line-width'].value + values['outline-width'].value * 2
        color = values.has_key('outline-color') and values['outline-color'].value

        opacity = values.has_key('outline-opacity') and values['outline-opacity'].value or None
        join = values.has_key('outline-join') and values['outline-join'].value or None
        cap = values.has_key('outline-cap') and values['outline-cap'].value or None
        dashes = values.has_key('outline-dasharray') and values['outline-dasharray'].value or None

        outline_symbolizer = color and width and output.LineSymbolizer(color, width, opacity, join, cap, dashes) or False
        
        if outline_symbolizer or line_symbolizer or inline_symbolizer:
            rules.append(make_rule(filter, outline_symbolizer, line_symbolizer, inline_symbolizer))

    return rules

def get_text_rule_groups(declarations, **kwargs):
    """ Given a list of declarations, return a list of output.Rule objects.
    """
    property_map = {'text-face-name': 'face_name',
                    'text-fontset': 'fontset',
                    'text-size': 'size', 
                    'text-ratio': 'text_ratio', 'text-wrap-width': 'wrap_width', 'text-spacing': 'spacing',
                    'text-label-position-tolerance': 'label_position_tolerance','text-transform':'text_transform',
                    'text-max-char-angle-delta': 'max_char_angle_delta', 'text-fill': 'fill',
                    'text-halo-fill': 'halo_fill', 'text-halo-radius': 'halo_radius',
                    'text-dx': 'dx', 'text-dy': 'dy', 'text-character-spacing': 'character_spacing',
                    'text-line-spacing': 'line_spacing',
                    'text-avoid-edges': 'avoid_edges', 'text-min-distance': 'min_distance',
                    'text-allow-overlap': 'allow_overlap', 'text-placement': 'placement',
                    'text-meta-output': 'meta-output', 'text-meta-writer': 'meta-writer'}

    property_names = property_map.keys()
    
    # pull out all the names
    text_names = [dec.selector.elements[1].names[0]
                  for dec in declarations
                  if len(dec.selector.elements) is 2 and len(dec.selector.elements[1].names) is 1]
    
    # a place to put groups
    groups = []
    
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
        
        # a place to put rules
        rules = []
        
        for (filter, values) in filtered_property_declarations(name_declarations, property_names):
            
            face_name = values.has_key('text-face-name') and values['text-face-name'].value or None
            fontset = values.has_key('text-fontset') and values['text-fontset'].value or None
            size = values.has_key('text-size') and values['text-size'].value
            color = values.has_key('text-fill') and values['text-fill'].value
            
            ratio = values.has_key('text-ratio') and values['text-ratio'].value or None
            wrap_width = values.has_key('text-wrap-width') and values['text-wrap-width'].value or None
            spacing = values.has_key('text-spacing') and values['text-spacing'].value or None
            label_position_tolerance = values.has_key('text-label-position-tolerance') and values['text-label-position-tolerance'].value or None
            max_char_angle_delta = values.has_key('text-max-char-angle-delta') and values['text-max-char-angle-delta'].value or None
            halo_color = values.has_key('text-halo-fill') and values['text-halo-fill'].value or None
            halo_radius = values.has_key('text-halo-radius') and values['text-halo-radius'].value or None
            dx = values.has_key('text-dx') and values['text-dx'].value or None
            dy = values.has_key('text-dy') and values['text-dy'].value or None
            avoid_edges = values.has_key('text-avoid-edges') and values['text-avoid-edges'].value or None
            min_distance = values.has_key('text-min-distance') and values['text-min-distance'].value or None
            allow_overlap = values.has_key('text-allow-overlap') and values['text-allow-overlap'].value or None
            placement = values.has_key('text-placement') and values['text-placement'].value or None
            text_transform = values.has_key('text-transform') and values['text-transform'].value or None
            
            if (face_name or fontset) and size and color:
                symbolizer = output.TextSymbolizer(text_name, face_name, size, color, \
                                              wrap_width, spacing, label_position_tolerance, \
                                              max_char_angle_delta, halo_color, halo_radius, dx, dy, \
                                              avoid_edges, min_distance, allow_overlap, placement, \
                                              text_transform, fontset=fontset)
            
                rules.append(make_rule(filter, symbolizer))
        
        groups.append((text_name, rules))
    
    return dict(groups)

def locally_cache_remote_file(href, dir):
    """
    """
    scheme, n, path, p, q, f = urlparse.urlparse(href)

    head, ext = os.path.splitext(path)
    
    (handle, local_path) = tempfile.mkstemp(prefix='cascadenik-', suffix=ext, dir=dir)
    os.write(handle, urllib.urlopen(href).read())
    os.close(handle)

    return local_path

def postprocess_symbolizer_image_file(file_href, target_dir, **kwargs):
    """ Given a file name and an output directory name, save the image
        file to a temporary location while noting its dimensions.
    """
    scheme, n, path, p, q, f = urlparse.urlparse(file_href)

    if scheme == 'http':
        scheme, path = '', locally_cache_remote_file(file_href, target_dir)
        
    if scheme not in ('file', '') or not os.path.exists(path):
        raise Exception("you're not helping")
    
    rel_path = os.path.relpath(path, target_dir)

    if path.startswith('/'):
        path = path
    elif rel_path.startswith('../'):
        path = os.path.join(target_dir, path)
    else:
        path = rel_path

    msg('reading symbol: %s' % path)

    target_dir = kwargs.get('target_dir',tempfile.gettempdir())
    
    image_name, ext = os.path.splitext(path)
    
    # support latest mapnik features of auto-detection
    # of image sizes and jpeg reading support...
    # http://trac.mapnik.org/ticket/508
    ver = kwargs.get('mapnik_version', None)
    mapnik_auto_image_support = (ver >= 700)

    if ext in ('.png', 'tif', 'tiff'):
        target_ext = ext
    else:
        target_ext = '.png'

    # new local file name
    dest_file = '%s%s' % (image_name, target_ext)

    msg('Destination file: %s' % dest_file)
        
    # throw error if we need to detect image sizes and can't because pil is missing
    if not mapnik_auto_image_support and not Image:
        raise SystemExit('PIL (Python Imaging Library) is required for handling image data unless you are using PNG inputs and running Mapnik >=0.7.0')

    # okay, we actually need read the data into memory now
    img_data = open(path,'rb').read()
    im = Image.open(StringIO.StringIO(img_data))

    im.save(dest_file)
    os.chmod(dest_file, 0644)

    return dest_file, target_ext[1:], im.size[0], im.size[1]

def get_shield_rule_groups(declarations, **kwargs):
    """ Given a list of declarations, return a list of output.Rule objects.
        
        Optionally provide an output directory for local copies of image files.
    """
    property_map = {'shield-face-name': 'face_name',
                    'shield-fontset': 'fontset',
                    'shield-size': 'size', 
                    'shield-fill': 'fill', 'shield-character-spacing': 'character_spacing',
                    'shield-line-spacing': 'line_spacing',
                    'shield-spacing': 'spacing', 'shield-min-distance': 'min_distance',
                    'shield-file': 'file', 'shield-width': 'width', 'shield-height': 'height',
                    'shield-meta-output': 'meta-output', 'shield-meta-writer': 'meta-writer'}

    property_names = property_map.keys()
    
    # pull out all the names
    text_names = [dec.selector.elements[1].names[0]
                  for dec in declarations
                  if len(dec.selector.elements) is 2 and len(dec.selector.elements[1].names) is 1]
    
    # a place to put groups
    groups = []
    
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
        
        # a place to put rules
        rules = []
        
        for (filter, values) in filtered_property_declarations(name_declarations, property_names):
        
            face_name = values.has_key('shield-face-name') and values['shield-face-name'].value or None
            fontset = values.has_key('shield-fontset') and values['shield-fontset'].value or None
            size = values.has_key('shield-size') and values['shield-size'].value or None
            
            file, filetype, width, height \
                = values.has_key('shield-file') \
                and postprocess_symbolizer_image_file(str(values['shield-file'].value), **kwargs) \
                or (None, None, None, None)
            
            width = values.has_key('shield-width') and values['shield-width'].value or width
            height = values.has_key('shield-height') and values['shield-height'].value or height
            
            color = values.has_key('shield-fill') and values['shield-fill'].value or None
            min_distance = values.has_key('shield-min-distance') and values['shield-min-distance'].value or None
            
            character_spacing = values.has_key('shield-character-spacing') and values['shield-character-spacing'].value or None
            line_spacing = values.has_key('shield-line-spacing') and values['shield-line-spacing'].value or None
            spacing = values.has_key('shield-spacing') and values['shield-spacing'].value or None
            
            if file or ((face_name or fontset) and size):
                symbolizer = output.ShieldSymbolizer(text_name, face_name, size, file, filetype, 
                                            width, height, color, min_distance,
                                            character_spacing, line_spacing, spacing,
                                            fontset=fontset)
            
                rules.append(make_rule(filter, symbolizer))
        
        groups.append((text_name, rules))
    
    return dict(groups)

def get_point_rules(declarations, **kwargs):
    """ Given a list of declarations, return a list of output.Rule objects.
        
        Optionally provide an output directory for local copies of image files.
    """
    property_map = {'point-file': 'file', 'point-width': 'width',
                    'point-height': 'height', 'point-type': 'type',
                    'point-allow-overlap': 'allow_overlap',
                    'point-meta-output': 'meta-output', 'point-meta-writer': 'meta-writer'}
    
    property_names = property_map.keys()
    
    # a place to put rules
    rules = []
    
    for (filter, values) in filtered_property_declarations(declarations, property_names):
        point_file, point_type, point_width, point_height \
            = values.has_key('point-file') \
            and postprocess_symbolizer_image_file(str(values['point-file'].value), **kwargs) \
            or (None, None, None, None)
        
        point_width = values.has_key('point-width') and values['point-width'].value or point_width
        point_height = values.has_key('point-height') and values['point-height'].value or point_height
        point_allow_overlap = values.has_key('point-allow-overlap') and values['point-allow-overlap'].value or None
        
        symbolizer = point_file and output.PointSymbolizer(point_file, point_type, point_width, point_height, point_allow_overlap)

        if symbolizer:
            rules.append(make_rule(filter, symbolizer))
    
    return rules

def get_polygon_pattern_rules(declarations, **kwargs):
    """ Given a list of declarations, return a list of output.Rule objects.
        
        Optionally provide an output directory for local copies of image files.
    """
    property_map = {'polygon-pattern-file': 'file', 'polygon-pattern-width': 'width',
                    'polygon-pattern-height': 'height', 'polygon-pattern-type': 'type',
                    'polygon-meta-output': 'meta-output', 'polygon-meta-writer': 'meta-writer'}

    
    property_names = property_map.keys()
    
    # a place to put rules
    rules = []
    
    for (filter, values) in filtered_property_declarations(declarations, property_names):
    
        poly_pattern_file, poly_pattern_type, poly_pattern_width, poly_pattern_height \
            = values.has_key('polygon-pattern-file') \
            and postprocess_symbolizer_image_file(str(values['polygon-pattern-file'].value), **kwargs) \
            or (None, None, None, None)
        
        poly_pattern_width = values.has_key('polygon-pattern-width') and values['polygon-pattern-width'].value or poly_pattern_width
        poly_pattern_height = values.has_key('polygon-pattern-height') and values['polygon-pattern-height'].value or poly_pattern_height
        symbolizer = poly_pattern_file and output.PolygonPatternSymbolizer(poly_pattern_file, poly_pattern_type, poly_pattern_width, poly_pattern_height)
        
        if symbolizer:
            rules.append(make_rule(filter, symbolizer))
    
    return rules

def get_line_pattern_rules(declarations, **kwargs):
    """ Given a list of declarations, return a list of output.Rule objects.
        
        Optionally provide an output directory for local copies of image files.
    """
    property_map = {'line-pattern-file': 'file', 'line-pattern-width': 'width',
                    'line-pattern-height': 'height', 'line-pattern-type': 'type',
                    'line-pattern-meta-output': 'meta-output', 'line-pattern-meta-writer': 'meta-writer'}

    
    property_names = property_map.keys()
    
    # a place to put rules
    rules = []
    
    for (filter, values) in filtered_property_declarations(declarations, property_names):
    
        line_pattern_file, line_pattern_type, line_pattern_width, line_pattern_height \
            = values.has_key('line-pattern-file') \
            and postprocess_symbolizer_image_file(str(values['line-pattern-file'].value), **kwargs) \
            or (None, None, None, None)
        
        line_pattern_width = values.has_key('line-pattern-width') and values['line-pattern-width'].value or line_pattern_width
        line_pattern_height = values.has_key('line-pattern-height') and values['line-pattern-height'].value or line_pattern_height
        symbolizer = line_pattern_file and output.LinePatternSymbolizer(line_pattern_file, line_pattern_type, line_pattern_width, line_pattern_height)
        
        if symbolizer:
            rules.append(make_rule(filter, symbolizer))
    
    return rules

def get_applicable_declarations(element, declarations):
    """ Given an XML element and a list of declarations, return the ones
        that match as a list of (property, value, selector) tuples.
    """
    element_tag = element.tag
    element_id = element.get('id', None)
    element_classes = element.get('class', '').split()

    return [dec for dec in declarations
            if dec.selector.matches(element_tag, element_id, element_classes)]

# TODO - unfinished work around moving local shapefiles
#def handle_shapefile_parts(shapefile,target_dir):
#    if not os.path.exists(target_dir):
#        os.mkdir(target_dir)
#    for (expected, required) in SHAPE_PARTS:
#        if required and expected not in extensions:
#            raise Exception('Shapefile %(shapefile)s missing extension "%(expected)s"' % locals())
#        
#        name = os.path.splitext(shapefile)[0]
#        source = os.path.normpath('%(target_dir)s/%(basename)s' % locals())
#        dest = os.path.normpath('%(target_dir)s/%(basename)s' % locals())
#        
#        shutil.copy()

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
    #else:
    #    return handle_shapefile_parts(shapefile,target_dir)


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

def localize_datasource(src, filename, **kwargs):
    """ Handle localizing file-based datasources other than zipped shapefiles.
    
    This will only work for single-file based types.
    """
    (scheme, netloc, path, params, query, fragment) = urlparse.urlparse(filename)

    move_local_files = kwargs.get('move_local_files')
    if move_local_files:
        sys.stderr.write('WARNING: moving local datasource files not yet supported\n')

    if scheme == '':
        # assumed to be local
        if kwargs.get('mapnik_version',None) >= 601:
            # Mapnik 0.6.1 accepts relative paths, so we leave it unchanged
            # but compiled file must maintain same relativity to the files
            # as the stylesheet, which needs to be addressed separately
            return filename
        else:
            msg('Warning, your Mapnik version is old and does not support relative paths to datasources')
            return os.path.realpath(urlparse.urljoin(src, filename))

    target_dir = kwargs.get('target_dir',tempfile.gettempdir())
    
    # if no-cache is True we avoid caching otherwise
    # we attempt to pull targets locally without re-downloading
    caching = not kwargs.get('no_cache',None)

    if kwargs.get('safe_urls'):
        target_dir = os.path.join(target_dir,url2fs(filename))

    target_file = os.path.join(target_dir,os.path.basename(filename))
    
    if caching:
        if kwargs.get('safe_urls'):
            if not os.path.isdir(target_dir):
                # does not exist yet
                msg('Downloading %s to base64 encoded dir: %s' % (filename,target_dir))
            else:
                # already downloaded, we can pull shapefile name from cache
                msg('File found, pulling from base64 encoded directory cache instead of downloading')
                return target_file
        else:
            # TODO - should we support zipped archives for non-shapefile datasources?
            if os.path.exists(target_file):
                return target_file
    else:
        msg('Avoiding searching for cached local files...')
        msg('Placing "%s" at "%s"' % (filename,target_dir))

    if not os.path.exists(target_dir):
        os.mkdir(target_dir)
    # use urllib2 here so 404's throw
    remote_file_data = urllib2.urlopen(filename).read()
    file_ = open(target_file, 'wb')
    file_.write(remote_file_data)
    file_.close()
    return target_file

def auto_detect_mapnik_version():
    mapnik = None
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

    try:
        # guessing src is a literal XML string?
        map_el = ElementTree.fromstring(src)
        base = None
    except:
        # or a URL or file location?
        doc = ElementTree.parse(urllib.urlopen(src))
        map_el = doc.getroot()

        if src.startswith('http://') or src.startswith('file://'):
            base = src
        else:
            base = 'file://' + os.path.realpath(src)

        base = src
            
    declarations = extract_declarations(map_el, base)
    
    # a list of layers and a sequential ID generator
    layers, ids = [], (i for i in xrange(1, 999999))
    
    for layer_el in map_el.findall('Layer'):
    
        # nevermind with this one
        if layer_el.get('status', None) in ('off', '0', 0):
            continue
        
        for parameter_el in layer_el.find('Datasource').findall('Parameter'):
            if parameter_el.get('name', None) == 'table':
                # remove line breaks from possible SQL
                # http://trac.mapnik.org/ticket/173
                if not kwargs.get('mapnik_version') >= 601:
                    parameter_el.text = parameter_el.text.replace('\r', ' ').replace('\n', ' ')
            elif parameter_el.get('name', None) == 'file':
                # make sure we localize any remote files
                if parameter_el.get('type', None) == 'shape':
                    # handle a local shapefile or fetch a remote, zipped shapefile
                    msg('Handling shapefile datasource...')
                    parameter_el.text = localize_shapefile(src, parameter_el.text, **kwargs)
                    # TODO - support datasource reprojection to make map srs
                    # TODO - support automatically indexing shapefiles
                else: # ogr,raster, gdal, sqlite
                    # attempt to generically handle other file based datasources
                    msg('Handling generic datasource...')
                    parameter_el.text = localize_datasource(src, parameter_el.text, **kwargs)

            # TODO - consider custom support for other mapnik datasources:
            # sqlite, oracle, osm, kismet, gdal, raster, rasterlite

        layer_declarations = get_applicable_declarations(layer_el, declarations)
        
        # a list of styles
        styles = []
        
        styles.append(output.Style('polygon style %d' % ids.next(),
                                   get_polygon_rules(layer_declarations, **kwargs)))

        styles.append(output.Style('polygon pattern style %d' % ids.next(),
                                   get_polygon_pattern_rules(layer_declarations, **kwargs)))

        styles.append(output.Style('raster style %d' % ids.next(),
                           get_raster_rules(layer_declarations,**kwargs)))

        styles.append(output.Style('line style %d' % ids.next(),
                                   get_line_rules(layer_declarations, **kwargs)))

        styles.append(output.Style('line pattern style %d' % ids.next(),
                                   get_line_pattern_rules(layer_declarations, **kwargs)))

        for (shield_name, shield_rules) in get_shield_rule_groups(layer_declarations, **kwargs).items():
            styles.append(output.Style('shield style %d (%s)' % (ids.next(), shield_name), shield_rules))

        for (text_name, text_rules) in get_text_rule_groups(layer_declarations, **kwargs).items():
            styles.append(output.Style('text style %d (%s)' % (ids.next(), text_name), text_rules))

        styles.append(output.Style('point style %d' % ids.next(),
                                   get_point_rules(layer_declarations, **kwargs)))
                                   
        styles = [s for s in styles if s.rules]
        
        if styles:
            datasource_params = dict([(p.get('name'), p.text) for p in layer_el.find('Datasource').findall('Parameter')])
            datasource = output.Datasource(**datasource_params)
            
            layer = output.Layer('layer %d' % ids.next(),
                                 datasource, styles,
                                 layer_el.get('srs', None),
                                 layer_el.get('min_zoom', None) and int(layer_el.get('min_zoom')) or None,
                                 layer_el.get('max_zoom', None) and int(layer_el.get('max_zoom')) or None)
    
            layers.append(layer)
    
    map_attrs = get_map_attributes(get_applicable_declarations(map_el, declarations))
    
    # if a target srs is profiled, override whatever is in mml
    if kwargs.get('srs'):
        map_el.set('srs',kwargs.get('srs'))
    
    return output.Map(map_el.attrib.get('srs', None), layers, **map_attrs)
