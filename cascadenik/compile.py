import os, sys
import math
import urllib
import urllib2
import tempfile
import StringIO
import operator
import base64
import posixpath
import os.path as systempath
import zipfile
import shutil

from hashlib import md5
from datetime import datetime
from time import strftime, localtime
from re import sub, compile, MULTILINE
from urlparse import urlparse, urljoin
from operator import lt, le, eq, ge, gt

# os.path.relpath was added in Python 2.6
def _relpath(path, start=posixpath.curdir):
    """Return a relative version of a path"""
    if not path:
        raise ValueError("no path specified")
    start_list = posixpath.abspath(start).split(posixpath.sep)
    path_list = posixpath.abspath(path).split(posixpath.sep)
    i = len(posixpath.commonprefix([start_list, path_list]))
    rel_list = [posixpath.pardir] * (len(start_list)-i) + path_list[i:]
    if not rel_list:
        return posixpath.curdir
    return posixpath.join(*rel_list)

# timeout parameter to HTTPConnection was added in Python 2.6
if sys.hexversion >= 0x020600F0:
    from httplib import HTTPConnection, HTTPSConnection

else:
    posixpath.relpath = _relpath
    
    from httplib import HTTPConnection as _HTTPConnection
    from httplib import HTTPSConnection as _HTTPSConnection
    import socket
    
    def HTTPConnection(host, port=None, strict=None, timeout=None):
        if timeout:
            socket.setdefaulttimeout(timeout)
        return _HTTPConnection(host, port=port, strict=strict)

    def HTTPSConnection(host, port=None, strict=None, timeout=None):
        if timeout:
            socket.setdefaulttimeout(timeout)
        return _HTTPSConnection(host, port=port, strict=strict)


# cascadenik
from . import safe64, style, output, sources
from . import MAPNIK_VERSION, MAPNIK_VERSION_STR
from .nonposix import un_posix, to_posix
from .parse import stylesheet_declarations
from .style import uri

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
    uri, extension = posixpath.splitext(url)
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

class Directories:
    """ Holder for full paths to output and cache dirs.
    """
    def __init__(self, output, cache, source):
        self.output = posixpath.realpath(to_posix(output))
        self.cache = posixpath.realpath(to_posix(cache))

        scheme, n, path, p, q, f = urlparse(to_posix(source))
        
        if scheme in ('http','https'):
            self.source = source
        elif scheme in ('file', ''):
            # os.path (systempath) usage here is intentional...
            self.source = 'file://' + to_posix(systempath.realpath(path))
        assert self.source, "self.source does not exist: source was: %s" % source

    def output_path(self, path_name):
        """ Modify a path so it fits expectations.
        
            Avoid returning relative paths that start with '../' and possibly
            return relative paths when output and cache directories match.
        """        
        # make sure it is a valid posix format
        path = to_posix(path_name)
        
        assert (path == path_name), "path_name passed to output_path must be in posix format"
        
        if posixpath.isabs(path):
            if self.output == self.cache:
                # worth seeing if an absolute path can be avoided
                path = posixpath.relpath(path, self.output)

            else:
                return posixpath.realpath(path)
    
        if path.startswith('../'):
            joined = posixpath.join(self.output, path)
            return posixpath.realpath(joined)
    
        return path

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

def is_merc_projection(srs):
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

def extract_declarations(map_el, dirs, scale=1):
    """ Given a Map element and directories object, remove and return a complete
        list of style declarations from any Stylesheet elements found within.
    """
    declarations = []
    
    for stylesheet in map_el.findall('Stylesheet'):
        map_el.remove(stylesheet)

        styles, mss_href = fetch_embedded_or_remote_src(stylesheet, dirs)

        if not styles:
            continue
            
        is_merc = is_merc_projection(map_el.get('srs',''))
        
        for declaration in stylesheet_declarations(styles, is_merc, scale):

            #
            # Change the value of each URI relative to the location
            # of the containing stylesheet. We generally just have
            # the one instance of "dirs" around for a full parse cycle,
            # so it's necessary to perform this normalization here
            # instead of later, while mss_href is still available.
            #
            uri_value = declaration.value.value
            
            if uri_value.__class__ is uri:
                uri_value.address = urljoin(mss_href, uri_value.address)

            declarations.append(declaration)

    return declarations

def fetch_embedded_or_remote_src(elem, dirs):
    """
    """
    if 'src' in elem.attrib:
        scheme, host, remote_path, p, q, f = urlparse(dirs.source)
        src_href = urljoin(dirs.source.rstrip('/')+'/', elem.attrib['src'])
        return urllib.urlopen(src_href).read().decode(DEFAULT_ENCODING), src_href

    elif elem.text:
        return elem.text, dirs.source.rstrip('/')+'/'
    
    return None, None

def expand_source_declarations(map_el, dirs, local_conf):
    """ This provides mechanism for externalizing and sharing data sources.  The datasource configs are
    python files, and layers reference sections within that config:
    
    <DataSourcesConfig src="datasources.cfg" />
    <Layer class="road major" source_name="planet_osm_major_roads" />
    <Layer class="road minor" source_name="planet_osm_minor_roads" />
    
    See example_dscfg.mml and example.cfg at the root of the cascadenik directory for an example.
    """

    
    
    ds = sources.DataSources(dirs.source, local_conf)

    # build up the configuration
    for spec in map_el.findall('DataSourcesConfig'):
        map_el.remove(spec)
        src_text, local_base = fetch_embedded_or_remote_src(spec, dirs)
        if not src_text:
            continue

        ds.add_config(src_text, local_base)    
    
    # now transform the xml

    # add in base datasources
    for base_name in ds.templates:
        b = Element("Datasource", name=base_name)
        for pname, pvalue in ds.sources[base_name]['parameters'].items():
            p = Element("Parameter", name=pname)
            p.text = str(pvalue)
            b.append(p)
        map_el.insert(0, b)
    
    # expand layer data sources
    for layer in map_el.findall('Layer'):
        if 'source_name' not in layer.attrib:
            continue
        
        if layer.attrib['source_name'] not in ds.sources:
            raise Exception("Datasource '%s' referenced, but not defined in layer:\n%s" % (layer.attrib['source_name'], ElementTree.tostring(layer)))
                
        # create the nested datasource object 
        b = Element("Datasource")
        dsrc = ds.sources[layer.attrib['source_name']]

        if 'template' in dsrc:
            b.attrib['base'] = dsrc['template']
        
        # set the SRS if present
        if 'layer_srs' in dsrc:
            layer.attrib['srs'] = dsrc['layer_srs']
        
        for pname, pvalue in dsrc['parameters'].items():
            p = Element("Parameter", name=pname)
            p.text = pvalue
            b.append(p)
        
        layer.append(b)
        del layer.attrib['source_name']
        
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

def get_map_attributes(declarations):
    """
    """
    property_map = {'map-bgcolor': 'background'}    
    
    return dict([(property_map[dec.property.name], dec.value.value)
                 for dec in declarations
                 if dec.property.name in property_map])

def filtered_property_declarations(declarations, property_names):
    """
    """
    property_names += ['display']

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
                
                # Presence of display: none means don't add this rule at all.
                if (dec.property.name, dec.value.value) == ('display', 'none'):
                    rule = {}
                    break

        # Presence of display here probably just means display: map,
        # which is boring and can be discarded.
        if rule and 'display' in rule:
            del rule['display']
        
        # If the rule is empty by this point, skip it.
        if not rule:
            continue

        rules.append((filter, rule))
    
    return rules

def get_polygon_rules(declarations):
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

def get_raster_rules(declarations):
    """ Given a Map element, a Layer element, and a list of declarations,
        create a new Style element with a RasterSymbolizer, add it to Map
        and refer to it in Layer.
        
        The RasterSymbolizer will always created, even if there are
        no applicable declarations.
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

    if not rules:
        # No raster-* rules were created, but we're here so we must need a symbolizer.
        rules.append(make_rule(Filter(), output.RasterSymbolizer()))
    
    return rules

def get_line_rules(declarations):
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

def get_text_rule_groups(declarations):
    """ Given a list of declarations, return a list of output.Rule objects.
    """
    property_map = {'text-anchor-dx': 'anchor_dx', # does nothing
                    'text-anchor-dy': 'anchor_dy', # does nothing
                    'text-align': 'horizontal_alignment',
                    'text-allow-overlap': 'allow_overlap',
                    'text-avoid-edges': 'avoid_edges',
                    'text-character-spacing': 'character_spacing',
                    'text-dx': 'dx',
                    'text-dy': 'dy',
                    'text-face-name': 'face_name',
                    'text-fill': 'fill',
                    'text-fontset': 'fontset',
                    'text-force-odd-labels': 'force_odd_labels',
                    'text-halo-fill': 'halo_fill',
                    'text-halo-radius': 'halo_radius',
                    'text-justify-align': 'justify_alignment',
                    'text-label-position-tolerance': 'label_position_tolerance',
                    'text-line-spacing': 'line_spacing',
                    'text-max-char-angle-delta': 'max_char_angle_delta',
                    'text-min-distance': 'minimum_distance',
                    'text-placement': 'label_placement',
                    'text-ratio': 'text_ratio',
                    'text-size': 'size', 
                    'text-spacing': 'spacing',
                    'text-transform': 'text_convert',
                    'text-vertical-align': 'vertical_alignment',
                    'text-wrap-width': 'wrap_width',
                    'text-meta-output': 'meta-output',
                    'text-meta-writer': 'meta-writer'
                    }

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
            label_spacing = values.has_key('text-spacing') and values['text-spacing'].value or None
            label_position_tolerance = values.has_key('text-label-position-tolerance') and values['text-label-position-tolerance'].value or None
            max_char_angle_delta = values.has_key('text-max-char-angle-delta') and values['text-max-char-angle-delta'].value or None
            halo_color = values.has_key('text-halo-fill') and values['text-halo-fill'].value or None
            halo_radius = values.has_key('text-halo-radius') and values['text-halo-radius'].value or None
            dx = values.has_key('text-dx') and values['text-dx'].value or None
            dy = values.has_key('text-dy') and values['text-dy'].value or None
            avoid_edges = values.has_key('text-avoid-edges') and values['text-avoid-edges'].value or None
            minimum_distance = values.has_key('text-min-distance') and values['text-min-distance'].value or None
            allow_overlap = values.has_key('text-allow-overlap') and values['text-allow-overlap'].value or None
            label_placement = values.has_key('text-placement') and values['text-placement'].value or None
            text_transform = values.has_key('text-transform') and values['text-transform'].value or None
            anchor_dx = values.has_key('text-anchor-dx') and values['text-anchor-dx'].value or None
            anchor_dy = values.has_key('text-anchor-dy') and values['text-anchor-dy'].value or None
            horizontal_alignment = values.has_key('text-horizontal-align') and values['text-horizontal-align'].value or None
            vertical_alignment = values.has_key('text-vertical-align') and values['text-vertical-align'].value or None
            justify_alignment = values.has_key('text-justify-align') and values['text-justify-align'].value or None
            force_odd_labels = values.has_key('text-force-odd-labels') and values['text-force-odd-labels'].value or None
            line_spacing = values.has_key('text-line-spacing') and values['text-line-spacing'].value or None
            character_spacing = values.has_key('text-character-spacing') and values['text-character-spacing'].value or None
            
            if (face_name or fontset) and size and color:
                symbolizer = output.TextSymbolizer(text_name, face_name, size, color, \
                                              wrap_width, label_spacing, label_position_tolerance, \
                                              max_char_angle_delta, halo_color, halo_radius, dx, dy, \
                                              avoid_edges, minimum_distance, allow_overlap, label_placement, \
                                              line_spacing, character_spacing, text_transform, fontset,
                                              anchor_dx, anchor_dy,horizontal_alignment, \
                                              vertical_alignment, justify_alignment, force_odd_labels)
            
                rules.append(make_rule(filter, symbolizer))
        
        groups.append((text_name, rules))
    
    return dict(groups)

def locally_cache_remote_file(href, dir):
    """ Locally cache a remote resource using a predictable file name
        and awareness of modification date. Assume that files are "normal"
        which is to say they have filenames with extensions.
    """
    scheme, host, remote_path, params, query, fragment = urlparse(href)
    
    assert scheme in ('http','https'), 'Scheme must be either http or https, not "%s" (for %s)' % (scheme,href)

    head, ext = posixpath.splitext(posixpath.basename(remote_path))
    head = sub(r'[^\w\-_]', '', head)
    hash = md5(href).hexdigest()[:8]
    
    local_path = '%(dir)s/%(host)s-%(hash)s-%(head)s%(ext)s' % locals()

    headers = {}
    if posixpath.exists(local_path):
        msg('Found local file: %s' % local_path )
        t = localtime(os.stat(local_path).st_mtime)
        headers['If-Modified-Since'] = strftime('%a, %d %b %Y %H:%M:%S %Z', t)
    
    if scheme == 'https':
        conn = HTTPSConnection(host, timeout=5)
    else:
        conn = HTTPConnection(host, timeout=5)

    if query:
        remote_path += '?%s' % query

    conn.request('GET', remote_path, headers=headers)
    resp = conn.getresponse()
        
    if resp.status in range(200, 210):
        # hurrah, it worked
        f = open(un_posix(local_path), 'wb')
        msg('Reading from remote: %s' % remote_path)
        f.write(resp.read())
        f.close()

    elif resp.status in (301, 302, 303) and resp.getheader('location', False):
        # follow a redirect, totally untested.
        redirected_href = urljoin(href, resp.getheader('location'))
        redirected_path = locally_cache_remote_file(redirected_href, dir)
        os.rename(redirected_path, local_path)
    
    elif resp.status == 304:
        # hurrah, it's cached
        msg('Reading directly from local cache')
        pass

    else:
        raise Exception("Failed to get remote resource %s: %s" % (href, resp.status))
    
    return local_path

def post_process_symbolizer_image_file(file_href, dirs):
    """ Given an image file href and a set of directories, modify the image file
        name so it's correct with respect to the output and cache directories.
    """
    # support latest mapnik features of auto-detection
    # of image sizes and jpeg reading support...
    # http://trac.mapnik.org/ticket/508

    mapnik_auto_image_support = (MAPNIK_VERSION >= 701)
    mapnik_requires_absolute_paths = (MAPNIK_VERSION < 601)
    file_href = urljoin(dirs.source.rstrip('/')+'/', file_href)
    scheme, n, path, p, q, f = urlparse(file_href)
    if scheme in ('http','https'):
        scheme, path = '', locally_cache_remote_file(file_href, dirs.cache)
    
    if scheme not in ('file', '') or not systempath.exists(un_posix(path)):
        raise Exception("Image file needs to be a working, fetchable resource, not %s" % file_href)
        
    if not mapnik_auto_image_support and not Image:
        raise SystemExit('PIL (Python Imaging Library) is required for handling image data unless you are using PNG inputs and running Mapnik >=0.7.0')

    img = Image.open(un_posix(path))
    
    if mapnik_requires_absolute_paths:
        path = posixpath.realpath(path)
    
    else:
        path = dirs.output_path(path)

    msg('reading symbol: %s' % path)

    image_name, ext = posixpath.splitext(path)
    
    if ext in ('.png', '.tif', '.tiff'):
        output_ext = ext
    else:
        output_ext = '.png'
    
    # new local file name
    dest_file = un_posix('%s%s' % (image_name, output_ext))
    
    if not posixpath.exists(dest_file):
        img.save(dest_file,'PNG')

    msg('Destination file: %s' % dest_file)

    return dest_file, output_ext[1:], img.size[0], img.size[1]

def get_shield_rule_groups(declarations, dirs):
    """ Given a list of declarations, return a list of output.Rule objects.
        
        Optionally provide an output directory for local copies of image files.
    """
    property_map = {'shield-face-name': 'face_name',
                    'shield-fontset': 'fontset',
                    'shield-size': 'size', 
                    'shield-fill': 'fill', 'shield-character-spacing': 'character_spacing',
                    'shield-line-spacing': 'line_spacing',
                    'shield-spacing': 'spacing', 'shield-min-distance': 'minimum_distance',
                    'shield-file': 'file', 'shield-width': 'width', 'shield-height': 'height',
                    'shield-meta-output': 'meta-output', 'shield-meta-writer': 'meta-writer',
                    'shield-text-dx': 'dx', 'shield-text-dy': 'dy'}

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
                and post_process_symbolizer_image_file(str(values['shield-file'].value), dirs) \
                or (None, None, None, None)
            
            width = values.has_key('shield-width') and values['shield-width'].value or width
            height = values.has_key('shield-height') and values['shield-height'].value or height
            
            color = values.has_key('shield-fill') and values['shield-fill'].value or None
            minimum_distance = values.has_key('shield-min-distance') and values['shield-min-distance'].value or None
            
            character_spacing = values.has_key('shield-character-spacing') and values['shield-character-spacing'].value or None
            line_spacing = values.has_key('shield-line-spacing') and values['shield-line-spacing'].value or None
            label_spacing = values.has_key('shield-spacing') and values['shield-spacing'].value or None
            
            text_dx = values.has_key('shield-text-dx') and values['shield-text-dx'].value or 0
            text_dy = values.has_key('shield-text-dy') and values['shield-text-dy'].value or 0
            
            if file and (face_name or fontset):
                symbolizer = output.ShieldSymbolizer(text_name, face_name, size, file, filetype, 
                                            width, height, color, minimum_distance, character_spacing,
                                            line_spacing, label_spacing, text_dx=text_dx, text_dy=text_dy,
                                            fontset=fontset)
            
                rules.append(make_rule(filter, symbolizer))
        
        groups.append((text_name, rules))
    
    return dict(groups)

def get_point_rules(declarations, dirs):
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
            and post_process_symbolizer_image_file(str(values['point-file'].value), dirs) \
            or (None, None, None, None)
        
        point_width = values.has_key('point-width') and values['point-width'].value or point_width
        point_height = values.has_key('point-height') and values['point-height'].value or point_height
        point_allow_overlap = values.has_key('point-allow-overlap') and values['point-allow-overlap'].value or None
        
        symbolizer = point_file and output.PointSymbolizer(point_file, point_type, point_width, point_height, point_allow_overlap)

        if symbolizer:
            rules.append(make_rule(filter, symbolizer))
    
    return rules

def get_polygon_pattern_rules(declarations, dirs):
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
            and post_process_symbolizer_image_file(str(values['polygon-pattern-file'].value), dirs) \
            or (None, None, None, None)
        
        poly_pattern_width = values.has_key('polygon-pattern-width') and values['polygon-pattern-width'].value or poly_pattern_width
        poly_pattern_height = values.has_key('polygon-pattern-height') and values['polygon-pattern-height'].value or poly_pattern_height
        symbolizer = poly_pattern_file and output.PolygonPatternSymbolizer(poly_pattern_file, poly_pattern_type, poly_pattern_width, poly_pattern_height)
        
        if symbolizer:
            rules.append(make_rule(filter, symbolizer))
    
    return rules

def get_line_pattern_rules(declarations, dirs):
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
            and post_process_symbolizer_image_file(str(values['line-pattern-file'].value), dirs) \
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

def unzip_shapefile_into(zip_path, dir, host=None):
    """
    """
    hash = md5(zip_path).hexdigest()[:8]
    zip_file = zipfile.ZipFile(un_posix(zip_path))
    zip_ctime = os.stat(un_posix(zip_path)).st_ctime
    
    infos = zip_file.infolist()
    extensions = [posixpath.splitext(info.filename)[1] for info in infos]
    
    host_prefix = host and ('%(host)s-' % locals()) or ''
    shape_parts = ('.shp', True), ('.shx', True), ('.dbf', True), ('.prj', False), ('.index', False)
    
    for (expected, required) in shape_parts:
        if required and expected not in extensions:
            raise Exception('Zip file %(zip_path)s missing extension "%(expected)s"' % locals())

        for info in infos:
            head, ext = posixpath.splitext(posixpath.basename(info.filename))
            head = sub(r'[^\w\-_]', '', head)

            if ext == expected:
                file_data = zip_file.read(info.filename)
                file_name = '%(dir)s/%(host_prefix)s%(hash)s-%(head)s%(ext)s' % locals()
                
                if not systempath.exists(un_posix(file_name)) or os.stat(un_posix(file_name)).st_ctime < zip_ctime:
                    file_ = open(un_posix(file_name), 'wb')
                    file_.write(file_data)
                    file_.close()
                
                if ext == '.shp':
                    local = file_name[:-4]
                
                break

    return local

def localize_shapefile(shp_href, dirs):
    """ Given a shapefile href and a set of directories, modify the shapefile
        name so it's correct with respect to the output and cache directories.
    """
    # support latest mapnik features of auto-detection
    # of image sizes and jpeg reading support...
    # http://trac.mapnik.org/ticket/508

    mapnik_requires_absolute_paths = (MAPNIK_VERSION < 601)

    shp_href = urljoin(dirs.source.rstrip('/')+'/', shp_href)
    scheme, host, path, p, q, f = urlparse(shp_href)
    
    if scheme in ('http','https'):
        msg('%s | %s' % (shp_href, dirs.cache))
        scheme, path = '', locally_cache_remote_file(shp_href, dirs.cache)
    else:
        host = None
    
    # collect drive for windows
    to_posix(systempath.realpath(path))

    if scheme not in ('file', ''):
        raise Exception("Shapefile needs to be local, not %s" % shp_href)
        
    if mapnik_requires_absolute_paths:
        path = posixpath.realpath(path)
        original = path

    path = dirs.output_path(path)
    
    if path.endswith('.zip'):
        # unzip_shapefile_into needs a path it can find
        path = posixpath.join(dirs.output, path)
        path = unzip_shapefile_into(path, dirs.cache, host)

    return dirs.output_path(path)

def localize_file_datasource(file_href, dirs):
    """ Handle localizing file-based datasources other than shapefiles.
    
        This will only work for single-file based types.
    """
    # support latest mapnik features of auto-detection
    # of image sizes and jpeg reading support...
    # http://trac.mapnik.org/ticket/508

    mapnik_requires_absolute_paths = (MAPNIK_VERSION < 601)

    file_href = urljoin(dirs.source.rstrip('/')+'/', file_href)
    scheme, n, path, p, q, f = urlparse(file_href)
    
    if scheme in ('http','https'):
        scheme, path = '', locally_cache_remote_file(file_href, dirs.cache)

    if scheme not in ('file', ''):
        raise Exception("Datasource file needs to be a working, fetchable resource, not %s" % file_href)

    if mapnik_requires_absolute_paths:
        return posixpath.realpath(path)
    
    else:
        return dirs.output_path(path)
    
def compile(src, dirs, verbose=False, srs=None, datasources_cfg=None, scale=1):
    """ Compile a Cascadenik MML file, returning a cascadenik.output.Map object.
    
        Parameters:
        
          src:
            Path to .mml file, or raw .mml file content.
          
          dirs:
            Object with directory names in 'cache', 'output', and 'source' attributes.
            dirs.source is expected to be fully-qualified, e.g. "http://example.com"
            or "file:///home/example".
        
        Keyword Parameters:
        
          verbose:
            If True, debugging information will be printed to stderr.
        
          srs:
            Target spatial reference system for the compiled stylesheet.
            If provided, overrides default map srs in the .mml file.
        
          datasources_cfg:
            If a file or URL, uses the config to override datasources or parameters
            (i.e. postgis_dbname) defined in the map's canonical <DataSourcesConfig>
            entities.  This is most useful in development, whereby one redefines
            individual datasources, connection parameters, and/or local paths.
        
          scale:
            Scale value for output map, 2 doubles the size for high-res displays.
    """
    global VERBOSE

    if verbose:
        VERBOSE = True
        sys.stderr.write('\n')
    
    msg('Targeting mapnik version: %s | %s' % (MAPNIK_VERSION, MAPNIK_VERSION_STR))
        
    if posixpath.exists(src):
        doc = ElementTree.parse(src)
        map_el = doc.getroot()
    else:
        try:
            # guessing src is a literal XML string?
            map_el = ElementTree.fromstring(src)
    
        except:
            if not (src[:7] in ('http://', 'https:/', 'file://')):
                src = "file://" + src
            try:
                doc = ElementTree.parse(urllib.urlopen(src))
            except IOError, e:
                raise IOError('%s: %s' % (e,src))
            map_el = doc.getroot()

    expand_source_declarations(map_el, dirs, datasources_cfg)
    declarations = extract_declarations(map_el, dirs, scale)
    
    # a list of layers and a sequential ID generator
    layers, ids = [], (i for i in xrange(1, 999999))


    # Handle base datasources
    # http://trac.mapnik.org/changeset/574
    datasource_templates = {}
    for base_el in map_el:
        if base_el.tag != 'Datasource':
            continue
        datasource_templates[base_el.get('name')] = dict(((p.get('name'),p.text) for p in base_el.findall('Parameter')))
    
    for layer_el in map_el.findall('Layer'):
    
        # nevermind with this one
        if layer_el.get('status', None) in ('off', '0', 0):
            continue

        # build up a map of Parameters for this Layer
        datasource_params = dict((p.get('name'),p.text) for p in layer_el.find('Datasource').findall('Parameter'))

        base = layer_el.find('Datasource').get('base')
        if base:
            datasource_params.update(datasource_templates[base])

        if datasource_params.get('table'):
            # remove line breaks from possible SQL, using a possibly-unsafe regexp
            # that simply blows away anything that looks like it might be a SQL comment.
            # http://trac.mapnik.org/ticket/173
            if not MAPNIK_VERSION >= 601:
                sql = datasource_params.get('table')
                sql = compile(r'--.*$', MULTILINE).sub('', sql)
                sql = sql.replace('\r', ' ').replace('\n', ' ')
                datasource_params['table'] = sql

        elif datasource_params.get('file') is not None:
            # make sure we localize any remote files
            file_param = datasource_params.get('file')

            if datasource_params.get('type') == 'shape':
                # handle a local shapefile or fetch a remote, zipped shapefile
                msg('Handling shapefile datasource...')
                file_param = localize_shapefile(file_param, dirs)

                # TODO - support datasource reprojection to make map srs
                # TODO - support automatically indexing shapefiles

            else: # ogr,raster, gdal, sqlite
                # attempt to generically handle other file based datasources
                msg('Handling generic datasource...')
                file_param = localize_file_datasource(file_param, dirs)

            msg("Localized path = %s" % un_posix(file_param))
            datasource_params['file'] = un_posix(file_param)

            # TODO - consider custom support for other mapnik datasources:
            # sqlite, oracle, osm, kismet, gdal, raster, rasterlite

        layer_declarations = get_applicable_declarations(layer_el, declarations)
        
        # a list of styles
        styles = []
        
        if datasource_params.get('type', None) == 'gdal':
            styles.append(output.Style('raster style %d' % ids.next(),
                                       get_raster_rules(layer_declarations)))
    
        else:
            styles.append(output.Style('polygon style %d' % ids.next(),
                                       get_polygon_rules(layer_declarations)))
    
            styles.append(output.Style('polygon pattern style %d' % ids.next(),
                                       get_polygon_pattern_rules(layer_declarations, dirs)))
    
            styles.append(output.Style('line style %d' % ids.next(),
                                       get_line_rules(layer_declarations)))
    
            styles.append(output.Style('line pattern style %d' % ids.next(),
                                       get_line_pattern_rules(layer_declarations, dirs)))
    
            for (shield_name, shield_rules) in get_shield_rule_groups(layer_declarations, dirs).items():
                styles.append(output.Style('shield style %d (%s)' % (ids.next(), shield_name), shield_rules))
    
            for (text_name, text_rules) in get_text_rule_groups(layer_declarations).items():
                styles.append(output.Style('text style %d (%s)' % (ids.next(), text_name), text_rules))
    
            styles.append(output.Style('point style %d' % ids.next(),
                                       get_point_rules(layer_declarations, dirs)))
                                   
        styles = [s for s in styles if s.rules]
        
        if styles:
            datasource = output.Datasource(**datasource_params)
            
            layer = output.Layer('layer %d' % ids.next(),
                                 datasource, styles,
                                 layer_el.get('srs', None),
                                 layer_el.get('min_zoom', None) and int(layer_el.get('min_zoom')) or None,
                                 layer_el.get('max_zoom', None) and int(layer_el.get('max_zoom')) or None)
    
            layers.append(layer)
    
    map_attrs = get_map_attributes(get_applicable_declarations(map_el, declarations))
    
    # if a target srs is profiled, override whatever is in mml
    if srs is not None:
        map_el.set('srs', srs)
    
    return output.Map(map_el.attrib.get('srs', None), layers, **map_attrs)
