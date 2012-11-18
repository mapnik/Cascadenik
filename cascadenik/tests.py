""" Tests for Cascadenik.

Run as a module, like this:
    python -m cascadenik.tests
"""
# -*- coding: utf-8 -*-

import os
import sys
import shutil
import urllib
import urlparse
import os.path
import unittest
import tempfile
import xml.etree.ElementTree

from .style import color, numbers, strings, boolean
from .style import Property, Selector, SelectorElement, SelectorAttributeTest
from .parse import ParseException, postprocess_value, stylesheet_declarations
from .compile import tests_filter_combinations, Filter, selectors_tests
from .compile import filtered_property_declarations, is_applicable_selector
from .compile import get_polygon_rules, get_line_rules, get_text_rule_groups, get_shield_rule_groups
from .compile import get_point_rules, get_polygon_pattern_rules, get_line_pattern_rules
from .compile import test2str, compile
from .compile import Directories
from .sources import DataSources
from . import mapnik, MAPNIK_VERSION
from . import output
    
class ParseTests(unittest.TestCase):
    
    def testBadSelector1(self):
        self.assertRaises(ParseException, stylesheet_declarations, 'Too Many Things { }')

    def testBadSelector2(self):
        self.assertRaises(ParseException, stylesheet_declarations, '{ }')

    def testBadSelector3(self):
        self.assertRaises(ParseException, stylesheet_declarations, 'Illegal { }')

    def testBadSelector4(self):
        self.assertRaises(ParseException, stylesheet_declarations, 'Layer foo[this=that] { }')

    def testBadSelector5(self):
        self.assertRaises(ParseException, stylesheet_declarations, 'Layer[this>that] foo { }')

    def testBadSelector6(self):
        self.assertRaises(ParseException, stylesheet_declarations, 'Layer foo#bar { }')

    def testBadSelector7(self):
        self.assertRaises(ParseException, stylesheet_declarations, 'Layer foo.bar { }')

    def testBadSelectorTest1(self):
        self.assertRaises(ParseException, stylesheet_declarations, 'Layer[foo>] { }')

    def testBadSelectorTest2(self):
        self.assertRaises(ParseException, stylesheet_declarations, 'Layer[foo><bar] { }')

    def testBadSelectorTest3(self):
        self.assertRaises(ParseException, stylesheet_declarations, 'Layer[foo<<bar] { }')

    def testBadSelectorTest4(self):
        self.assertRaises(ParseException, stylesheet_declarations, 'Layer[<bar] { }')

    def testBadSelectorTest5(self):
        self.assertRaises(ParseException, stylesheet_declarations, 'Layer[<<bar] { }')

    def testBadProperty1(self):
        self.assertRaises(ParseException, stylesheet_declarations, 'Layer { unknown-property: none; }')

    def testBadProperty2(self):
        self.assertRaises(ParseException, stylesheet_declarations, 'Layer { extra thing: none; }')

    def testBadProperty3(self):
        self.assertRaises(ParseException, stylesheet_declarations, 'Layer { "not an ident": none; }')

    def testBadNesting1(self):
        self.assertRaises(ParseException, stylesheet_declarations, 'Layer { .weird { line-width: 1; } }')

    def testBadNesting2(self):
        self.assertRaises(ParseException, stylesheet_declarations, 'Layer { #weird { line-width: 1; } }')

    def testBadNesting3(self):
        self.assertRaises(ParseException, stylesheet_declarations, 'Layer { [foo=bar] { line-width: 1; } }')

    def testBadNesting4(self):
        self.assertRaises(ParseException, stylesheet_declarations, 'Layer { &More { line-width: 1; } }')

    def testRulesets1(self):
        self.assertEqual(1, len(stylesheet_declarations('/* empty stylesheet */')))

    def testDeclarations2(self):
        self.assertEqual(2, len(stylesheet_declarations('Layer { line-width: 1; }')))

    def testDeclarations3(self):
        self.assertEqual(3, len(stylesheet_declarations('Layer { line-width: 1; } Layer { line-width: 1; }')))

    def testDeclarations4(self):
        self.assertEqual(4, len(stylesheet_declarations('Layer { line-width: 1; } /* something */ Layer { line-width: 1; } /* extra */ Layer { line-width: 1; }')))

    def testDeclarations5(self):
        self.assertEqual(2, len(stylesheet_declarations('Map { line-width: 1; }')))

class SelectorTests(unittest.TestCase):
    
    def testSpecificity1(self):
        self.assertEqual((0, 1, 0), Selector(SelectorElement(['Layer'])).specificity())
    
    def testSpecificity2(self):
        self.assertEqual((0, 2, 0), Selector(SelectorElement(['Layer']), SelectorElement(['name'])).specificity())
    
    def testSpecificity3(self):
        self.assertEqual((0, 2, 0), Selector(SelectorElement(['Layer', '.class'])).specificity())
    
    def testSpecificity4(self):
        self.assertEqual((0, 3, 0), Selector(SelectorElement(['Layer', '.class']), SelectorElement(['name'])).specificity())
    
    def testSpecificity5(self):
        self.assertEqual((1, 2, 0), Selector(SelectorElement(['Layer', '#id']), SelectorElement(['name'])).specificity())
    
    def testSpecificity6(self):
        self.assertEqual((1, 0, 0), Selector(SelectorElement(['#id'])).specificity())
    
    def testSpecificity7(self):
        self.assertEqual((1, 0, 1), Selector(SelectorElement(['#id'], [SelectorAttributeTest('a', '>', 'b')])).specificity())
    
    def testSpecificity8(self):
        self.assertEqual((1, 0, 2), Selector(SelectorElement(['#id'], [SelectorAttributeTest('a', '>', 'b'), SelectorAttributeTest('a', '<', 'b')])).specificity())

    def testSpecificity9(self):
        self.assertEqual((1, 0, 2), Selector(SelectorElement(['#id'], [SelectorAttributeTest('a', '>', 100), SelectorAttributeTest('a', '<', 'b')])).specificity())

    def testMatch1(self):
        assert Selector(SelectorElement(['Layer'])).matches('Layer', 'foo', [])

    def testMatch2(self):
        assert Selector(SelectorElement(['#foo'])).matches('Layer', 'foo', [])

    def testMatch3(self):
        assert not Selector(SelectorElement(['#foo'])).matches('Layer', 'bar', [])

    def testMatch4(self):
        assert Selector(SelectorElement(['.bar'])).matches('Layer', None, ['bar'])

    def testMatch5(self):
        assert Selector(SelectorElement(['.bar'])).matches('Layer', None, ['bar', 'baz'])

    def testMatch6(self):
        assert Selector(SelectorElement(['.bar', '.baz'])).matches('Layer', None, ['bar', 'baz'])

    def testMatch7(self):
        assert not Selector(SelectorElement(['.bar', '.baz'])).matches('Layer', None, ['bar'])

    def testMatch8(self):
        assert not Selector(SelectorElement(['Layer'])).matches('Map', None, [])

    def testMatch9(self):
        assert not Selector(SelectorElement(['Map'])).matches('Layer', None, [])

    def testMatch10(self):
        assert Selector(SelectorElement(['*'])).matches('Layer', None, [])

    def testMatch11(self):
        assert Selector(SelectorElement(['*'])).matches('Map', None, [])

    def testRange1(self):
        selector = Selector(SelectorElement(['*'], [SelectorAttributeTest('scale-denominator', '>', 100)]))
        assert selector.isRanged()
        assert not selector.inRange(99)
        assert not selector.inRange(100)
        assert selector.inRange(1000)

    def testRange2(self):
        selector = Selector(SelectorElement(['*'], [SelectorAttributeTest('scale-denominator', '>=', 100)]))
        assert selector.isRanged()
        assert selector.isMapScaled()
        assert not selector.inRange(99)
        assert selector.inRange(100)
        assert selector.inRange(1000)

    def testRange3(self):
        selector = Selector(SelectorElement(['*'], [SelectorAttributeTest('scale-denominator', '<', 100)]))
        assert selector.isRanged()
        assert selector.isMapScaled()
        assert selector.inRange(99)
        assert not selector.inRange(100)
        assert not selector.inRange(1000)

    def testRange4(self):
        selector = Selector(SelectorElement(['*'], [SelectorAttributeTest('scale-denominator', '<=', 100)]))
        assert selector.isRanged()
        assert selector.isMapScaled()
        assert selector.inRange(99)
        assert selector.inRange(100)
        assert not selector.inRange(1000)

    def testRange5(self):
        selector = Selector(SelectorElement(['*'], [SelectorAttributeTest('nonsense', '<=', 100)]))
        assert selector.isRanged()
        assert not selector.isMapScaled()
        assert selector.inRange(99)
        assert selector.inRange(100)
        assert not selector.inRange(1000)

    def testRange6(self):
        selector = Selector(SelectorElement(['*'], [SelectorAttributeTest('scale-denominator', '>=', 100), SelectorAttributeTest('scale-denominator', '<', 1000)]))
        assert selector.isRanged()
        assert selector.isMapScaled()
        assert not selector.inRange(99)
        assert selector.inRange(100)
        assert not selector.inRange(1000)

    def testRange7(self):
        selector = Selector(SelectorElement(['*'], [SelectorAttributeTest('scale-denominator', '>', 100), SelectorAttributeTest('scale-denominator', '<=', 1000)]))
        assert selector.isRanged()
        assert selector.isMapScaled()
        assert not selector.inRange(99)
        assert not selector.inRange(100)
        assert selector.inRange(1000)

    def testRange8(self):
        selector = Selector(SelectorElement(['*'], [SelectorAttributeTest('scale-denominator', '<=', 100), SelectorAttributeTest('scale-denominator', '>=', 1000)]))
        assert selector.isRanged()
        assert selector.isMapScaled()
        assert not selector.inRange(99)
        assert not selector.inRange(100)
        assert not selector.inRange(1000)

class ValueTests(unittest.TestCase):

    def testBadValue1(self):
        self.assertRaises(ParseException, postprocess_value, Property('polygon-opacity'), [], False, 0, 0)

    def testBadValue2(self):
        self.assertRaises(ParseException, postprocess_value, Property('polygon-opacity'), [('IDENT', 'too'), ('IDENT', 'many')], False, 0, 0)

    def testBadValue3(self):
        self.assertRaises(ParseException, postprocess_value, Property('polygon-opacity'), [('IDENT', 'non-number')], False, 0, 0)

    def testBadValue3b(self):
        self.assertRaises(ParseException, postprocess_value, Property('polygon-gamma'), [('IDENT', 'non-number')], False, 0, 0)

    def testBadValue4(self):
        self.assertRaises(ParseException, postprocess_value, Property('text-face-name'), [('IDENT', 'non-string')], False, 0, 0)

    def testBadValue5(self):
        self.assertRaises(ParseException, postprocess_value, Property('polygon-fill'), [('IDENT', 'non-hash')], False, 0, 0)

    def testBadValue6(self):
        self.assertRaises(ParseException, postprocess_value, Property('polygon-fill'), [('HASH', '#badcolor')], False, 0, 0)

    def testBadValue7(self):
        self.assertRaises(ParseException, postprocess_value, Property('point-file'), [('IDENT', 'non-URI')], False, 0, 0)

    def testBadValue8(self):
        self.assertRaises(ParseException, postprocess_value, Property('text-avoid-edges'), [('IDENT', 'bad-boolean')], False, 0, 0)

    def testBadValue9(self):
        self.assertRaises(ParseException, postprocess_value, Property('line-join'), [('STRING', 'not an IDENT')], False, 0, 0)

    def testBadValue10(self):
        self.assertRaises(ParseException, postprocess_value, Property('line-join'), [('IDENT', 'not-in-tuple')], False, 0, 0)

    def testBadValue11(self):
        self.assertRaises(ParseException, postprocess_value, Property('line-dasharray'), [('NUMBER', '1'), ('CHAR', ','), ('CHAR', ','), ('NUMBER', '3')], False, 0, 0)

    def testValue1(self):
        self.assertEqual(1.0, postprocess_value(Property('polygon-opacity'), [('NUMBER', '1.0')], False, 0, 0).value)

    def testValue1b(self):
        self.assertEqual(1.0, postprocess_value(Property('polygon-gamma'), [('NUMBER', '1.0')], False, 0, 0).value)

    def testValue2(self):
        self.assertEqual(10, postprocess_value(Property('line-width'), [('NUMBER', '10')], False, 0, 0).value)

    def testValue2b(self):
        self.assertEqual(-10, postprocess_value(Property('text-dx'), [('CHAR', '-'), ('NUMBER', '10')], False, 0, 0).value)

    def testValue3(self):
        self.assertEqual('DejaVu', str(postprocess_value(Property('text-face-name'), [('STRING', '"DejaVu"')], False, 0, 0)))

    def testValue4(self):
        self.assertEqual('#ff9900', str(postprocess_value(Property('map-bgcolor'), [('HASH', '#ff9900')], False, 0, 0)))

    def testValue5(self):
        self.assertEqual('#ff9900', str(postprocess_value(Property('map-bgcolor'), [('HASH', '#f90')], False, 0, 0)))

    def testValue6(self):
        self.assertEqual('http://example.com', str(postprocess_value(Property('point-file'), [('URI', 'url("http://example.com")')], False, 0, 0)))

    def testValue7(self):
        self.assertEqual('true', str(postprocess_value(Property('text-avoid-edges'), [('IDENT', 'true')], False, 0, 0)))

    def testValue8(self):
        self.assertEqual('false', str(postprocess_value(Property('text-avoid-edges'), [('IDENT', 'false')], False, 0, 0)))

    def testValue9(self):
        self.assertEqual('bevel', str(postprocess_value(Property('line-join'), [('IDENT', 'bevel')], False, 0, 0)))

    def testValue10(self):
        self.assertEqual('1,2,3', str(postprocess_value(Property('line-dasharray'), [('NUMBER', '1'), ('CHAR', ','), ('NUMBER', '2'), ('CHAR', ','), ('NUMBER', '3')], False, 0, 0)))

    def testValue11(self):
        self.assertEqual('1,2.0,3', str(postprocess_value(Property('line-dasharray'), [('NUMBER', '1'), ('CHAR', ','), ('S', ' '), ('NUMBER', '2.0'), ('CHAR', ','), ('NUMBER', '3')], False, 0, 0)))

    def testValue12(self):
        self.assertEqual(12, postprocess_value(Property('text-character-spacing'), [('NUMBER', '12')], False, 0, 0).value)

    def testValue13(self):
        self.assertEqual(14, postprocess_value(Property('shield-character-spacing'), [('NUMBER', '14')], False, 0, 0).value)

    def testValue14(self):
        self.assertEqual(12, postprocess_value(Property('text-line-spacing'), [('NUMBER', '12')], False, 0, 0).value)

    def testValue15(self):
        self.assertEqual(14, postprocess_value(Property('shield-line-spacing'), [('NUMBER', '14')], False, 0, 0).value)
    
class CascadeTests(unittest.TestCase):

    def testCascade1(self):
        s = """
            Layer
            {
                text-dx: -10;
                text-dy: -10;
            }
        """
        declarations = stylesheet_declarations(s)
        
        # ditch the boring display: map declaration
        declarations.pop(0)
        
        self.assertEqual(2, len(declarations))
        self.assertEqual(1, len(declarations[0].selector.elements))
        self.assertEqual('text-dx', declarations[0].property.name)
        self.assertEqual('text-dy', declarations[1].property.name)
        self.assertEqual(-10, declarations[1].value.value)

    def testCascade2(self):
        s = """
            * { text-fill: #ff9900 !important; }

            Layer#foo.foo[baz>10] bar,
            *
            {
                polygon-fill: #f90;
                text-face-name: /* boo yah */ "Helvetica Bold";
                text-size: 10;
                polygon-pattern-file: url('http://example.com');
                line-cap: square;
                text-allow-overlap: false;
                text-dx: -10;
                polygon-gamma: /* value between 0 and 1 */ .65;
                text-character-spacing: 4;
            }
        """
        declarations = stylesheet_declarations(s)
        
        # ditch the boring display: map declaration
        declarations.pop(0)
        
        # first declaration is the unimportant polygon-fill: #f90
        self.assertEqual(1, len(declarations[0].selector.elements))

        # last declaration is the !important one, text-fill: #ff9900
        self.assertEqual(1, len(declarations[-1].selector.elements))

        # second-last declaration is the highly-specific one, text-character-spacing
        self.assertEqual(2, len(declarations[-2].selector.elements))
        
        self.assertEqual(19, len(declarations))

        self.assertEqual('*', str(declarations[0].selector))
        self.assertEqual('polygon-fill', declarations[0].property.name)
        self.assertEqual('#ff9900', str(declarations[0].value))

        self.assertEqual('*', str(declarations[1].selector))
        self.assertEqual('text-face-name', declarations[1].property.name)
        self.assertEqual('Helvetica Bold', str(declarations[1].value))

        self.assertEqual('*', str(declarations[2].selector))
        self.assertEqual('text-size', declarations[2].property.name)
        self.assertEqual('10', str(declarations[2].value))

        self.assertEqual('*', str(declarations[3].selector))
        self.assertEqual('polygon-pattern-file', declarations[3].property.name)
        self.assertEqual('http://example.com', str(declarations[3].value))

        self.assertEqual('*', str(declarations[4].selector))
        self.assertEqual('line-cap', declarations[4].property.name)
        self.assertEqual('square', str(declarations[4].value))

        self.assertEqual('*', str(declarations[5].selector))
        self.assertEqual('text-allow-overlap', declarations[5].property.name)
        self.assertEqual('false', str(declarations[5].value))

        self.assertEqual('*', str(declarations[6].selector))
        self.assertEqual('text-dx', declarations[6].property.name)
        self.assertEqual('-10', str(declarations[6].value))

        self.assertEqual('*', str(declarations[7].selector))
        self.assertEqual('polygon-gamma', declarations[7].property.name)
        self.assertEqual('0.65', str(declarations[7].value))
        
        self.assertEqual('*', str(declarations[8].selector))
        self.assertEqual('text-character-spacing', declarations[8].property.name)
        self.assertEqual('4', str(declarations[8].value))
        
        self.assertEqual('Layer#foo.foo[baz>10] bar', str(declarations[9].selector))
        self.assertEqual('polygon-fill', declarations[9].property.name)
        self.assertEqual('#ff9900', str(declarations[9].value))

        self.assertEqual('Layer#foo.foo[baz>10] bar', str(declarations[10].selector))
        self.assertEqual('text-face-name', declarations[10].property.name)
        self.assertEqual('Helvetica Bold', str(declarations[10].value))

        self.assertEqual('Layer#foo.foo[baz>10] bar', str(declarations[11].selector))
        self.assertEqual('text-size', declarations[11].property.name)
        self.assertEqual('10', str(declarations[11].value))

        self.assertEqual('Layer#foo.foo[baz>10] bar', str(declarations[12].selector))
        self.assertEqual('polygon-pattern-file', declarations[12].property.name)
        self.assertEqual('http://example.com', str(declarations[12].value))

        self.assertEqual('Layer#foo.foo[baz>10] bar', str(declarations[13].selector))
        self.assertEqual('line-cap', declarations[13].property.name)
        self.assertEqual('square', str(declarations[13].value))

        self.assertEqual('Layer#foo.foo[baz>10] bar', str(declarations[14].selector))
        self.assertEqual('text-allow-overlap', declarations[14].property.name)
        self.assertEqual('false', str(declarations[14].value))

        self.assertEqual('Layer#foo.foo[baz>10] bar', str(declarations[15].selector))
        self.assertEqual('text-dx', declarations[15].property.name)
        self.assertEqual('-10', str(declarations[15].value))

        self.assertEqual('Layer#foo.foo[baz>10] bar', str(declarations[16].selector))
        self.assertEqual('polygon-gamma', declarations[16].property.name)
        self.assertEqual('0.65', str(declarations[16].value))

        self.assertEqual('*', str(declarations[18].selector))
        self.assertEqual('text-fill', declarations[18].property.name)
        self.assertEqual('#ff9900', str(declarations[18].value))

class SelectorParseTests(unittest.TestCase):

    def testFilters1(self):
        s = """
            Layer[landuse=military] { polygon-fill: #000; }
        """
        selectors = [dec.selector for dec in stylesheet_declarations(s)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual("[landuse] = 'military'", test2str(filters[1].tests[0]))

    def testFilters2(self):
        s = """
            Layer[landuse='military'] { polygon-fill: #000; }
        """
        selectors = [dec.selector for dec in stylesheet_declarations(s)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual("[landuse] = 'military'", test2str(filters[1].tests[0]))

    def testFilters3(self):
        s = """
            Layer[landuse="military"] { polygon-fill: #000; }
        """
        selectors = [dec.selector for dec in stylesheet_declarations(s)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual("[landuse] = 'military'", test2str(filters[1].tests[0]))

    def testFilters4(self):
        s = """
            Layer[foo=1] { polygon-fill: #000; }
        """
        selectors = [dec.selector for dec in stylesheet_declarations(s)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual("[foo] = 1", test2str(filters[1].tests[0]))

    def testFilters5(self):
        s = """
            Layer[foo=1.1] { polygon-fill: #000; }
        """
        selectors = [dec.selector for dec in stylesheet_declarations(s)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual("[foo] = 1.1", test2str(filters[1].tests[0]))

    def testFilters6(self):
        s = """
            Layer[foo="1.1"] { polygon-fill: #000; }
        """
        selectors = [dec.selector for dec in stylesheet_declarations(s)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual("[foo] = '1.1'", test2str(filters[1].tests[0]))

    def testFilters7(self):
        s = """
            Layer[landuse= "military"] { polygon-fill: #000; }
        """
        selectors = [dec.selector for dec in stylesheet_declarations(s)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual("[landuse] = 'military'", test2str(filters[1].tests[0]))

    def testFilters8(self):
        s = """
            Layer[foo =1] { polygon-fill: #000; }
        """
        selectors = [dec.selector for dec in stylesheet_declarations(s)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual("[foo] = 1", test2str(filters[1].tests[0]))

    def testFilters9(self):
        s = """
            Layer[foo = "1.1"] { polygon-fill: #000; }
        """
        selectors = [dec.selector for dec in stylesheet_declarations(s)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual("[foo] = '1.1'", test2str(filters[1].tests[0]))

    def testFilters10(self):
        # Unicode is fine in filter values
        # Not so much in properties
        s = u'''
        Layer[name="Grüner Strich"] { polygon-fill: #000; }
        '''
        selectors = [dec.selector for dec in stylesheet_declarations(s)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual(u"[name] = 'Grüner Strich'", test2str(filters[1].tests[0]))
        self.assert_(isinstance(filters[1].tests[0].value, unicode))
        self.assert_(isinstance(filters[1].tests[0].property, str))

    def testUnicode1(self):
        # Unicode is bad in property values
        s = u'''
        Layer CODE {
            text-face-name: "DejaVu Sans Book";
            text-size: 12; 
            text-fill: #005;
            text-placement: line;
        }
        '''
        declarations = stylesheet_declarations(s, is_merc=True)
        text_rule_groups = get_text_rule_groups(declarations)
        
        self.assertEqual(str, type(text_rule_groups.keys()[0]))
        self.assert_(isinstance(text_rule_groups['CODE'][0].symbolizers[0].face_name, strings))
        self.assertEqual(str, type(text_rule_groups['CODE'][0].symbolizers[0].label_placement))

class FilterCombinationTests(unittest.TestCase):

    def testFilters1(self):
        s = """
            Layer[landuse=military]     { polygon-fill: #000; }
            Layer[landuse=civilian]     { polygon-fill: #001; }
            Layer[landuse=agriculture]  { polygon-fill: #010; }
        """
        selectors = [dec.selector for dec in stylesheet_declarations(s)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual(len(filters), 4)
        self.assertEqual(str(sorted(filters)), '[[landuse!=agriculture][landuse!=civilian][landuse!=military], [landuse=agriculture], [landuse=civilian], [landuse=military]]')

    def testFilters2(self):
        s = """
            Layer[landuse=military]     { polygon-fill: #000; }
            Layer[landuse=civilian]     { polygon-fill: #001; }
            Layer[landuse=agriculture]  { polygon-fill: #010; }
            Layer[horse=yes]    { polygon-fill: #011; }
        """
        selectors = [dec.selector for dec in stylesheet_declarations(s)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual(len(filters), 8)
        self.assertEqual(str(sorted(filters)), '[[horse!=yes][landuse!=agriculture][landuse!=civilian][landuse!=military], [horse!=yes][landuse=agriculture], [horse!=yes][landuse=civilian], [horse!=yes][landuse=military], [horse=yes][landuse!=agriculture][landuse!=civilian][landuse!=military], [horse=yes][landuse=agriculture], [horse=yes][landuse=civilian], [horse=yes][landuse=military]]')

    def testFilters3(self):
        s = """
            Layer[landuse=military]     { polygon-fill: #000; }
            Layer[landuse=civilian]     { polygon-fill: #001; }
            Layer[landuse=agriculture]  { polygon-fill: #010; }
            Layer[horse=yes]    { polygon-fill: #011; }
            Layer[horse=no]     { polygon-fill: #100; }
        """
        selectors = [dec.selector for dec in stylesheet_declarations(s)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual(len(filters), 12)
        self.assertEqual(str(sorted(filters)), '[[horse!=no][horse!=yes][landuse!=agriculture][landuse!=civilian][landuse!=military], [horse!=no][horse!=yes][landuse=agriculture], [horse!=no][horse!=yes][landuse=civilian], [horse!=no][horse!=yes][landuse=military], [horse=no][landuse!=agriculture][landuse!=civilian][landuse!=military], [horse=no][landuse=agriculture], [horse=no][landuse=civilian], [horse=no][landuse=military], [horse=yes][landuse!=agriculture][landuse!=civilian][landuse!=military], [horse=yes][landuse=agriculture], [horse=yes][landuse=civilian], [horse=yes][landuse=military]]')

    def testFilters4(self):
        s = """
            Layer[landuse=military]     { polygon-fill: #000; }
            Layer[landuse=civilian]     { polygon-fill: #001; }
            Layer[landuse=agriculture]  { polygon-fill: #010; }
            Layer[horse=yes]    { polygon-fill: #011; }
            Layer[leisure=park] { polygon-fill: #100; }
        """
        selectors = [dec.selector for dec in stylesheet_declarations(s)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual(len(filters), 16)
        self.assertEqual(str(sorted(filters)), '[[horse!=yes][landuse!=agriculture][landuse!=civilian][landuse!=military][leisure!=park], [horse!=yes][landuse!=agriculture][landuse!=civilian][landuse!=military][leisure=park], [horse!=yes][landuse=agriculture][leisure!=park], [horse!=yes][landuse=agriculture][leisure=park], [horse!=yes][landuse=civilian][leisure!=park], [horse!=yes][landuse=civilian][leisure=park], [horse!=yes][landuse=military][leisure!=park], [horse!=yes][landuse=military][leisure=park], [horse=yes][landuse!=agriculture][landuse!=civilian][landuse!=military][leisure!=park], [horse=yes][landuse!=agriculture][landuse!=civilian][landuse!=military][leisure=park], [horse=yes][landuse=agriculture][leisure!=park], [horse=yes][landuse=agriculture][leisure=park], [horse=yes][landuse=civilian][leisure!=park], [horse=yes][landuse=civilian][leisure=park], [horse=yes][landuse=military][leisure!=park], [horse=yes][landuse=military][leisure=park]]')

class NestedRuleTests(unittest.TestCase):

    def testCompile1(self):
        s = """
            Layer
            {
                &.red { polygon-fill: #f00 }
                &.blue { polygon-fill: #00f }
            }
        """
        declarations = stylesheet_declarations(s)
        
        self.assertEqual(len(declarations), 3)
        
        self.assertEqual(len(declarations[1].selector.elements), 1)
        self.assertEqual(len(declarations[2].selector.elements), 1)
        
        self.assertEqual(declarations[1].selector.elements[0].names[0], 'Layer')
        self.assertEqual(declarations[1].selector.elements[0].names[1], '.red')
        self.assertEqual((declarations[1].property.name, str(declarations[1].value.value)), ('polygon-fill', '#ff0000'))
        
        self.assertEqual(declarations[2].selector.elements[0].names[0], 'Layer')
        self.assertEqual(declarations[2].selector.elements[0].names[1], '.blue')
        self.assertEqual((declarations[2].property.name, str(declarations[2].value.value)), ('polygon-fill', '#0000ff'))

    def testCompile2(self):
        s = """
            .north, .south
            {
                &.east, &.west
                {
                    polygon-fill: #f90
                }
            }
        """
        declarations = stylesheet_declarations(s)
        
        self.assertEqual(len(declarations), 5)
        
        self.assertEqual(len(declarations[1].selector.elements), 1)
        self.assertEqual(len(declarations[2].selector.elements), 1)
        self.assertEqual(len(declarations[3].selector.elements), 1)
        self.assertEqual(len(declarations[4].selector.elements), 1)
        
        self.assertEqual(declarations[1].selector.elements[0].names[0], '.north')
        self.assertEqual(declarations[1].selector.elements[0].names[1], '.east')
        self.assertEqual((declarations[1].property.name, str(declarations[1].value.value)), ('polygon-fill', '#ff9900'))
        
        self.assertEqual(declarations[2].selector.elements[0].names[0], '.north')
        self.assertEqual(declarations[2].selector.elements[0].names[1], '.west')
        self.assertEqual((declarations[2].property.name, str(declarations[2].value.value)), ('polygon-fill', '#ff9900'))
        
        self.assertEqual(declarations[3].selector.elements[0].names[0], '.south')
        self.assertEqual(declarations[3].selector.elements[0].names[1], '.east')
        self.assertEqual((declarations[3].property.name, str(declarations[3].value.value)), ('polygon-fill', '#ff9900'))
        
        self.assertEqual(declarations[4].selector.elements[0].names[0], '.south')
        self.assertEqual(declarations[4].selector.elements[0].names[1], '.west')
        self.assertEqual((declarations[4].property.name, str(declarations[4].value.value)), ('polygon-fill', '#ff9900'))

    def testCompile3(self):
        s = """
            .roads
            {
                line-color: #f90;
            
                &[kind=highway] { line-width: 3 }
                &[kind=major] { line-width: 2 }
                &[kind=minor] { line-width: 1 }
            }
        """
        declarations = stylesheet_declarations(s)
        
        self.assertEqual(len(declarations), 5)
        
        self.assertEqual(len(declarations[1].selector.elements), 1)
        self.assertEqual(len(declarations[2].selector.elements), 1)
        self.assertEqual(len(declarations[3].selector.elements), 1)
        self.assertEqual(len(declarations[4].selector.elements), 1)
        
        self.assertEqual(declarations[1].selector.elements[0].names[0], '.roads')
        self.assertEqual((declarations[1].property.name, str(declarations[1].value.value)), ('line-color', '#ff9900'))
        
        self.assertEqual(declarations[2].selector.elements[0].names[0], '.roads')
        self.assertEqual(str(declarations[2].selector.elements[0].tests[0]), '[kind=highway]')
        self.assertEqual((declarations[2].property.name, declarations[2].value.value), ('line-width', 3))
        
        self.assertEqual(declarations[3].selector.elements[0].names[0], '.roads')
        self.assertEqual(str(declarations[3].selector.elements[0].tests[0]), '[kind=major]')
        self.assertEqual((declarations[3].property.name, declarations[3].value.value), ('line-width', 2))
        
        self.assertEqual(declarations[4].selector.elements[0].names[0], '.roads')
        self.assertEqual(str(declarations[4].selector.elements[0].tests[0]), '[kind=minor]')
        self.assertEqual((declarations[4].property.name, declarations[4].value.value), ('line-width', 1))

    def testCompile4(self):
        s = """
            .roads
            {
                text-fill: #f90;
            
                &[kind=highway] name { text-size: 24 }
                &[kind=major] name { text-size: 18 }
                &[kind=minor] name { text-size: 12 }
            }
        """
        declarations = stylesheet_declarations(s)
        
        self.assertEqual(len(declarations), 5)
        
        self.assertEqual(len(declarations[1].selector.elements), 1)
        self.assertEqual(len(declarations[2].selector.elements), 2)
        self.assertEqual(len(declarations[3].selector.elements), 2)
        self.assertEqual(len(declarations[4].selector.elements), 2)
        
        self.assertEqual(declarations[1].selector.elements[0].names[0], '.roads')
        self.assertEqual((declarations[1].property.name, str(declarations[1].value.value)), ('text-fill', '#ff9900'))
        
        self.assertEqual(declarations[2].selector.elements[0].names[0], '.roads')
        self.assertEqual(str(declarations[2].selector.elements[0].tests[0]), '[kind=highway]')
        self.assertEqual(declarations[2].selector.elements[1].names[0], 'name')
        self.assertEqual((declarations[2].property.name, declarations[2].value.value), ('text-size', 24))
        
        self.assertEqual(declarations[3].selector.elements[0].names[0], '.roads')
        self.assertEqual(str(declarations[3].selector.elements[0].tests[0]), '[kind=major]')
        self.assertEqual(declarations[3].selector.elements[1].names[0], 'name')
        self.assertEqual((declarations[3].property.name, declarations[3].value.value), ('text-size', 18))
        
        self.assertEqual(declarations[4].selector.elements[0].names[0], '.roads')
        self.assertEqual(str(declarations[4].selector.elements[0].tests[0]), '[kind=minor]')
        self.assertEqual(declarations[4].selector.elements[1].names[0], 'name')
        self.assertEqual((declarations[4].property.name, declarations[4].value.value), ('text-size', 12))

    def testCompile5(self):
        s = """
            #roads
            {
                &[level=1]
                {
                    &[level=2]
                    {
                        &[level=3]
                        {
                            &.deep[level=4]
                            {
                                name
                                {
                                    text-size: 12;
                                }
                            }
                        }
                    }
                }
            }
        """
        declarations = stylesheet_declarations(s)
        
        self.assertEqual(len(declarations), 2)
        
        self.assertEqual(len(declarations[1].selector.elements), 2)
        self.assertEqual(len(declarations[1].selector.elements[0].names), 2)
        self.assertEqual(len(declarations[1].selector.elements[0].tests), 4)
        self.assertEqual(len(declarations[1].selector.elements[1].names), 1)
        self.assertEqual(len(declarations[1].selector.elements[1].tests), 0)
        
        self.assertEqual(declarations[1].selector.elements[0].names[0], '#roads')
        self.assertEqual(declarations[1].selector.elements[0].names[1], '.deep')
        self.assertEqual(str(declarations[1].selector.elements[0].tests[0]), '[level=1]')
        self.assertEqual(str(declarations[1].selector.elements[0].tests[1]), '[level=2]')
        self.assertEqual(str(declarations[1].selector.elements[0].tests[2]), '[level=3]')
        self.assertEqual(str(declarations[1].selector.elements[0].tests[3]), '[level=4]')
        
        self.assertEqual(declarations[1].selector.elements[1].names[0], 'name')
        
        self.assertEqual((declarations[1].property.name, declarations[1].value.value), ('text-size', 12))

    def testCompile6(self):
        s = """
            #low[zoom<5],
            #high[zoom>=5]
            {
                polygon-fill: #fff;
            
                &[zoom=0] { polygon-fill: #000; }
                &[zoom=3] { polygon-fill: #333; }
                &[zoom=6] { polygon-fill: #666; }
                &[zoom=9] { polygon-fill: #999; }
            }
        """
        
        declarations = stylesheet_declarations(s, is_merc=True)
        
        self.assertEqual(len(declarations), 11)
        
        for index in (1, 3, 5, 7, 9):
            self.assertEqual(str(declarations[index].selector.elements[0])[:33], '#low[scale-denominator>=26147868]')
        
        for index in (2, 4, 6, 8, 10):
            self.assertEqual(str(declarations[index].selector.elements[0])[:33], '#high[scale-denominator<26147868]')
        
        for index in (1, 2):
            self.assertEqual(str(declarations[index].value.value), '#ffffff')
        
        for index in (3, 4):
            self.assertEqual(str(declarations[index].selector.elements[0])[33:], '[scale-denominator>=418365887][scale-denominator<836731773]')
            self.assertEqual(str(declarations[index].value.value), '#000000')
        
        for index in (5, 6):
            self.assertEqual(str(declarations[index].selector.elements[0])[33:], '[scale-denominator>=52295736][scale-denominator<104591472]')
            self.assertEqual(str(declarations[index].value.value), '#333333')
        
        for index in (7, 8):
            self.assertEqual(str(declarations[index].selector.elements[0])[33:], '[scale-denominator>=6536967][scale-denominator<13073934]')
            self.assertEqual(str(declarations[index].value.value), '#666666')
        
        for index in (9, 10):
            self.assertEqual(str(declarations[index].selector.elements[0])[33:], '[scale-denominator>=817121][scale-denominator<1634242]')
            self.assertEqual(str(declarations[index].value.value), '#999999')

class AtVariableTests(unittest.TestCase):

    def testCompile1(self):
        s = """
            @orange: #f90;
            @blue : #00c;
            
            .orange { polygon-fill: @orange }
            .blue { polygon-fill: @blue }
        """
        
        declarations = stylesheet_declarations(s)
        
        self.assertEqual(len(declarations), 3)
        
        self.assertEqual(declarations[1].selector.elements[0].names[0], '.orange')
        self.assertEqual(str(declarations[1].value.value), '#ff9900')
        
        self.assertEqual(declarations[2].selector.elements[0].names[0], '.blue')
        self.assertEqual(str(declarations[2].value.value), '#0000cc')

    def testCompile2(self):
        s = """
            @blue: #00c;
            .dk-blue { polygon-fill: @blue }
        
            @blue: #06f;
            .lt-blue { polygon-fill: @blue }
        """
        
        declarations = stylesheet_declarations(s)
        
        self.assertEqual(len(declarations), 3)
        
        self.assertEqual(declarations[1].selector.elements[0].names[0], '.dk-blue')
        self.assertEqual(str(declarations[1].value.value), '#0000cc')
        
        self.assertEqual(declarations[2].selector.elements[0].names[0], '.lt-blue')
        self.assertEqual(str(declarations[2].value.value), '#0066ff')

class SimpleRangeTests(unittest.TestCase):

    def testRanges1(self):
        s = """
            Layer[foo<1000] { polygon-fill: #000; }
            Layer[foo>1000] { polygon-fill: #001; }
        """
        selectors = [dec.selector for dec in stylesheet_declarations(s)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual(len(filters), 3)
        self.assertEqual(str(sorted(filters)), '[[foo<1000], [foo=1000], [foo>1000]]')

    def testRanges2(self):
        s = """
            Layer[foo>1] { polygon-fill: #000; }
            Layer[foo<2] { polygon-fill: #001; }
        """
        selectors = [dec.selector for dec in stylesheet_declarations(s)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual(len(filters), 3)
        self.assertEqual(str(sorted(filters)), '[[foo<2][foo>1], [foo<=1], [foo>=2]]')

    def testRanges3(self):
        s = """
            Layer[foo>1] { polygon-fill: #000; }
            Layer[foo<2] { polygon-fill: #001; }
            Layer[bar>4] { polygon-fill: #010; }
            Layer[bar<8] { polygon-fill: #011; }
        """
        selectors = [dec.selector for dec in stylesheet_declarations(s)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual(len(filters), 9)
        self.assertEqual(str(sorted(filters)), '[[bar<8][bar>4][foo<2][foo>1], [bar<8][bar>4][foo<=1], [bar<8][bar>4][foo>=2], [bar<=4][foo<2][foo>1], [bar<=4][foo<=1], [bar<=4][foo>=2], [bar>=8][foo<2][foo>1], [bar>=8][foo<=1], [bar>=8][foo>=2]]')

    def testRanges4(self):
        s = """
            Layer[foo>1] { polygon-fill: #000; }
            Layer[foo<2] { polygon-fill: #001; }
            Layer[bar=this] { polygon-fill: #010; }
            Layer[bar=that] { polygon-fill: #011; }
        """
        selectors = [dec.selector for dec in stylesheet_declarations(s)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual(len(filters), 9)
        self.assertEqual(str(sorted(filters)), '[[bar!=that][bar!=this][foo<2][foo>1], [bar!=that][bar!=this][foo<=1], [bar!=that][bar!=this][foo>=2], [bar=that][foo<2][foo>1], [bar=that][foo<=1], [bar=that][foo>=2], [bar=this][foo<2][foo>1], [bar=this][foo<=1], [bar=this][foo>=2]]')

    def testRanges5(self):
        s = """
            Layer[foo>1] { polygon-fill: #000; }
            Layer[foo<2] { polygon-fill: #001; }
            Layer[bar=this] { polygon-fill: #010; }
            Layer[bar=that] { polygon-fill: #011; }
            Layer[bar=blah] { polygon-fill: #100; }
        """
        selectors = [dec.selector for dec in stylesheet_declarations(s)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual(len(filters), 12)
        self.assertEqual(str(sorted(filters)), '[[bar!=blah][bar!=that][bar!=this][foo<2][foo>1], [bar!=blah][bar!=that][bar!=this][foo<=1], [bar!=blah][bar!=that][bar!=this][foo>=2], [bar=blah][foo<2][foo>1], [bar=blah][foo<=1], [bar=blah][foo>=2], [bar=that][foo<2][foo>1], [bar=that][foo<=1], [bar=that][foo>=2], [bar=this][foo<2][foo>1], [bar=this][foo<=1], [bar=this][foo>=2]]')

class CompatibilityTests(unittest.TestCase):

    def testCompatibility1(self):
        a = SelectorAttributeTest('foo', '=', 1)
        b = SelectorAttributeTest('foo', '=', 1)
        assert a.isCompatible([b])
        assert b.isCompatible([a])

    def testCompatibility2(self):
        a = SelectorAttributeTest('foo', '=', 1)
        b = SelectorAttributeTest('bar', '=', 1)
        assert a.isCompatible([b])
        assert b.isCompatible([a])

    def testCompatibility3(self):
        a = SelectorAttributeTest('foo', '=', 1)
        b = SelectorAttributeTest('foo', '!=', 1)
        assert not a.isCompatible([b])
        assert not b.isCompatible([a])

    def testCompatibility4(self):
        a = SelectorAttributeTest('foo', '!=', 1)
        b = SelectorAttributeTest('bar', '=', 1)
        assert a.isCompatible([b])
        assert b.isCompatible([a])

    def testCompatibility5(self):
        a = SelectorAttributeTest('foo', '!=', 1)
        b = SelectorAttributeTest('foo', '!=', 2)
        assert a.isCompatible([b])
        assert b.isCompatible([a])

    def testCompatibility6(self):
        a = SelectorAttributeTest('foo', '!=', 1)
        b = SelectorAttributeTest('foo', '!=', 1)
        assert a.isCompatible([b])
        assert b.isCompatible([a])

    def testCompatibility7(self):
        a = SelectorAttributeTest('foo', '=', 1)
        b = SelectorAttributeTest('foo', '<', 1)
        assert not a.isCompatible([b])
        assert not b.isCompatible([a])

    def testCompatibility8(self):
        a = SelectorAttributeTest('foo', '>=', 1)
        b = SelectorAttributeTest('foo', '=', 1)
        assert a.isCompatible([b])
        assert b.isCompatible([a])

    def testCompatibility9(self):
        a = SelectorAttributeTest('foo', '=', 1)
        b = SelectorAttributeTest('foo', '<=', 1)
        assert a.isCompatible([b])
        assert b.isCompatible([a])

    def testCompatibility10(self):
        a = SelectorAttributeTest('foo', '>', 1)
        b = SelectorAttributeTest('foo', '=', 1)
        assert not a.isCompatible([b])
        assert not b.isCompatible([a])

    def testCompatibility11(self):
        a = SelectorAttributeTest('foo', '>', 2)
        b = SelectorAttributeTest('foo', '<=', 1)
        assert not a.isCompatible([b])
        assert not b.isCompatible([a])

    def testCompatibility12(self):
        a = SelectorAttributeTest('foo', '<=', 1)
        b = SelectorAttributeTest('foo', '>', 2)
        assert not a.isCompatible([b])
        assert not b.isCompatible([a])

    def testCompatibility13(self):
        a = SelectorAttributeTest('foo', '<', 1)
        b = SelectorAttributeTest('foo', '>', 1)
        assert not a.isCompatible([b])
        assert not b.isCompatible([a])

    def testCompatibility14(self):
        a = SelectorAttributeTest('foo', '<', 2)
        b = SelectorAttributeTest('foo', '>', 1)
        assert a.isCompatible([b])
        assert b.isCompatible([a])

    def testCompatibility15(self):
        # Layer[scale-denominator>1000][bar>1]
        s = Selector(SelectorElement(['Layer'], [SelectorAttributeTest('scale-denominator', '>', 1000), SelectorAttributeTest('bar', '<', 3)]))
        
        # [bar>=3][baz=quux][foo>1][scale-denominator>1000]
        f = Filter(SelectorAttributeTest('scale-denominator', '>', 1000), SelectorAttributeTest('bar', '>=', 3), SelectorAttributeTest('foo', '>', 1), SelectorAttributeTest('baz', '=', 'quux'))
        
        assert not is_applicable_selector(s, f)

    def testCompatibility16(self):
        # Layer[scale-denominator<1000][foo=1]
        s = Selector(SelectorElement(['Layer'], [SelectorAttributeTest('scale-denominator', '<', 1000), SelectorAttributeTest('foo', '=', 1)]))
        
        # [baz!=quux][foo=1][scale-denominator>1000]
        f = Filter(SelectorAttributeTest('baz', '!=', 'quux'), SelectorAttributeTest('foo', '=', 1), SelectorAttributeTest('scale-denominator', '>', 1000))
        
        assert not is_applicable_selector(s, f)

class StyleRuleTests(unittest.TestCase):

    def setUp(self):
        # a directory for all the temp files to be created below
        self.tmpdir = tempfile.mkdtemp(prefix='cascadenik-tests-')
        self.dirs = Directories(self.tmpdir, self.tmpdir, self.tmpdir)

    def tearDown(self):
        # destroy the above-created directory
        shutil.rmtree(self.tmpdir)

    def testStyleRules01(self):
        s = """
            Layer[zoom<=10][use=park] { polygon-fill: #0f0; }
            Layer[zoom<=10][use=cemetery] { polygon-fill: #999; }
            Layer[zoom>10][use=park] { polygon-fill: #6f6; }
            Layer[zoom>10][use=cemetery] { polygon-fill: #ccc; }
        """

        declarations = stylesheet_declarations(s, is_merc=True)
        rules = get_polygon_rules(declarations)
        
        self.assertEqual(408560, rules[0].maxscale.value)
        self.assertEqual(color(0xCC, 0xCC, 0xCC), rules[0].symbolizers[0].color)
        self.assertEqual("[use] = 'cemetery'", rules[0].filter.text)
        
        self.assertEqual(408560, rules[1].maxscale.value)
        self.assertEqual(color(0x66, 0xFF, 0x66), rules[1].symbolizers[0].color)
        self.assertEqual("[use] = 'park'", rules[1].filter.text)
    
        self.assertEqual(408561, rules[2].minscale.value)
        self.assertEqual(color(0x99, 0x99, 0x99), rules[2].symbolizers[0].color)
        self.assertEqual("[use] = 'cemetery'", rules[2].filter.text)
        
        self.assertEqual(408561, rules[3].minscale.value)
        self.assertEqual(color(0x00, 0xFF, 0x00), rules[3].symbolizers[0].color)
        self.assertEqual("[use] = 'park'", rules[3].filter.text)

    def testStyleRules02(self):
        s = """
            Layer[zoom<=10][foo<1] { polygon-fill: #000; }
            Layer[zoom<=10][foo>1] { polygon-fill: #00f; }
            Layer[zoom>10][foo<1] { polygon-fill: #0f0; }
            Layer[zoom>10][foo>1] { polygon-fill: #f00; }
        """
    
        declarations = stylesheet_declarations(s, is_merc=True)
        rules = get_polygon_rules(declarations)
        
        self.assertEqual(408560, rules[0].maxscale.value)
        self.assertEqual(color(0x00, 0xFF, 0x00), rules[0].symbolizers[0].color)
        self.assertEqual('[foo] < 1', rules[0].filter.text)
        
        self.assertEqual(408560, rules[1].maxscale.value)
        self.assertEqual(color(0xFF, 0x00, 0x00), rules[1].symbolizers[0].color)
        self.assertEqual('[foo] > 1', rules[1].filter.text)
    
        self.assertEqual(408561, rules[2].minscale.value)
        self.assertEqual(color(0x00, 0x00, 0x00), rules[2].symbolizers[0].color)
        self.assertEqual('[foo] < 1', rules[2].filter.text)
        
        self.assertEqual(408561, rules[3].minscale.value)
        self.assertEqual(color(0x00, 0x00, 0xFF), rules[3].symbolizers[0].color)
        self.assertEqual('[foo] > 1', rules[3].filter.text)

    def testStyleRules03(self):
        s = """
            Layer[zoom<=10][foo<1] { polygon-fill: #000; }
            Layer[zoom<=10][foo>1] { polygon-fill: #00f; }
            Layer[zoom>10][foo<1] { polygon-fill: #0f0; }
            Layer[zoom>10][foo>1] { polygon-fill: #f00; }
    
            Layer[zoom<=10] { line-width: 1; }
            Layer[zoom>10] { line-width: 2; }
            Layer[foo<1] { line-color: #0ff; }
            Layer[foo=1] { line-color: #f0f; }
            Layer[foo>1] { line-color: #ff0; }
        """
    
        declarations = stylesheet_declarations(s, is_merc=True)

        poly_rules = get_polygon_rules(declarations)
        
        self.assertEqual(408560, poly_rules[0].maxscale.value)
        self.assertEqual(color(0x00, 0xFF, 0x00), poly_rules[0].symbolizers[0].color)
        self.assertEqual('[foo] < 1', poly_rules[0].filter.text)
        
        self.assertEqual(408560, poly_rules[1].maxscale.value)
        self.assertEqual(color(0xFF, 0x00, 0x00), poly_rules[1].symbolizers[0].color)
        self.assertEqual('[foo] > 1', poly_rules[1].filter.text)
    
        self.assertEqual(408561, poly_rules[2].minscale.value)
        self.assertEqual(color(0x00, 0x00, 0x00), poly_rules[2].symbolizers[0].color)
        self.assertEqual('[foo] < 1', poly_rules[2].filter.text)
        
        self.assertEqual(408561, poly_rules[3].minscale.value)
        self.assertEqual(color(0x00, 0x00, 0xFF), poly_rules[3].symbolizers[0].color)
        self.assertEqual('[foo] > 1', poly_rules[3].filter.text)
        
        line_rules = get_line_rules(declarations)

        self.assertEqual(408560, line_rules[0].maxscale.value)
        self.assertEqual(color(0x00, 0xFF, 0xFF), line_rules[0].symbolizers[0].color)
        self.assertEqual(2.0, line_rules[0].symbolizers[0].width)
        self.assertEqual('[foo] < 1', line_rules[0].filter.text)
        
        self.assertEqual(408560, line_rules[1].maxscale.value)
        self.assertEqual(color(0xFF, 0x00, 0xFF), line_rules[1].symbolizers[0].color)
        self.assertEqual(2.0, line_rules[1].symbolizers[0].width)
        self.assertEqual('[foo] = 1', line_rules[1].filter.text)
    
        self.assertEqual(408560, line_rules[2].maxscale.value)
        self.assertEqual(color(0xFF, 0xFF, 0x00), line_rules[2].symbolizers[0].color)
        self.assertEqual(2.0, line_rules[2].symbolizers[0].width)
        self.assertEqual('[foo] > 1', line_rules[2].filter.text)
    
        self.assertEqual(408561, line_rules[3].minscale.value)
        self.assertEqual(color(0x00, 0xFF, 0xFF), line_rules[3].symbolizers[0].color)
        self.assertEqual(1.0, line_rules[3].symbolizers[0].width)
        self.assertEqual('[foo] < 1', line_rules[3].filter.text)
        
        self.assertEqual(408561, line_rules[4].minscale.value)
        self.assertEqual(color(0xFF, 0x00, 0xFF), line_rules[4].symbolizers[0].color)
        self.assertEqual(1.0, line_rules[4].symbolizers[0].width)
        self.assertEqual('[foo] = 1', line_rules[4].filter.text)
        
        self.assertEqual(408561, line_rules[5].minscale.value)
        self.assertEqual(color(0xFF, 0xFF, 0x00), line_rules[5].symbolizers[0].color)
        self.assertEqual(1.0, line_rules[5].symbolizers[0].width)
        self.assertEqual('[foo] > 1', line_rules[5].filter.text)

    def testStyleRules04(self):
        s = """
            Layer[zoom<=10] { line-width: 1; }
            Layer[zoom>10] { line-width: 2; }
            Layer[foo<1] { line-color: #0ff; }
            Layer[foo=1] { line-color: #f0f; }
            Layer[foo>1] { line-color: #ff0; }
            
            Layer label { text-face-name: 'Helvetica'; text-size: 12; text-fill: #000; }
            Layer[foo<1] label { text-face-name: 'Arial'; }
            Layer[zoom<=10] label { text-size: 10; }
        """
    
        declarations = stylesheet_declarations(s, is_merc=True)
        
        line_rules = get_line_rules(declarations)

        self.assertEqual(408560, line_rules[0].maxscale.value)
        self.assertEqual(color(0x00, 0xFF, 0xFF), line_rules[0].symbolizers[0].color)
        self.assertEqual(2.0, line_rules[0].symbolizers[0].width)
        self.assertEqual('[foo] < 1', line_rules[0].filter.text)
        
        self.assertEqual(408560, line_rules[1].maxscale.value)
        self.assertEqual(color(0xFF, 0x00, 0xFF), line_rules[1].symbolizers[0].color)
        self.assertEqual(2.0, line_rules[1].symbolizers[0].width)
        self.assertEqual('[foo] = 1', line_rules[1].filter.text)
    
        self.assertEqual(408560, line_rules[2].maxscale.value)
        self.assertEqual(color(0xFF, 0xFF, 0x00), line_rules[2].symbolizers[0].color)
        self.assertEqual(2.0, line_rules[2].symbolizers[0].width)
        self.assertEqual('[foo] > 1', line_rules[2].filter.text)
    
        self.assertEqual(408561, line_rules[3].minscale.value)
        self.assertEqual(color(0x00, 0xFF, 0xFF), line_rules[3].symbolizers[0].color)
        self.assertEqual(1.0, line_rules[3].symbolizers[0].width)
        self.assertEqual('[foo] < 1', line_rules[3].filter.text)
        
        self.assertEqual(408561, line_rules[4].minscale.value)
        self.assertEqual(color(0xFF, 0x00, 0xFF), line_rules[4].symbolizers[0].color)
        self.assertEqual(1.0, line_rules[4].symbolizers[0].width)
        self.assertEqual('[foo] = 1', line_rules[4].filter.text)
        
        self.assertEqual(408561, line_rules[5].minscale.value)
        self.assertEqual(color(0xFF, 0xFF, 0x00), line_rules[5].symbolizers[0].color)
        self.assertEqual(1.0, line_rules[5].symbolizers[0].width)
        self.assertEqual('[foo] > 1', line_rules[5].filter.text)
        
        text_rule_groups = get_text_rule_groups(declarations)
        
        self.assertEqual(408560, text_rule_groups['label'][0].maxscale.value)
        self.assertEqual(strings('Arial'), text_rule_groups['label'][0].symbolizers[0].face_name)
        self.assertEqual(12, text_rule_groups['label'][0].symbolizers[0].size)
        self.assertEqual('[foo] < 1', text_rule_groups['label'][0].filter.text)
        
        self.assertEqual(408560, text_rule_groups['label'][1].maxscale.value)
        self.assertEqual(strings('Helvetica'), text_rule_groups['label'][1].symbolizers[0].face_name)
        self.assertEqual(12, text_rule_groups['label'][1].symbolizers[0].size)
        self.assertEqual('[foo] >= 1', text_rule_groups['label'][1].filter.text)
    
        self.assertEqual(408561, text_rule_groups['label'][2].minscale.value)
        self.assertEqual(strings('Arial'), text_rule_groups['label'][2].symbolizers[0].face_name)
        self.assertEqual(10, text_rule_groups['label'][2].symbolizers[0].size)
        self.assertEqual('[foo] < 1', text_rule_groups['label'][2].filter.text)
        
        self.assertEqual(408561, text_rule_groups['label'][3].minscale.value)
        self.assertEqual(strings('Helvetica'), text_rule_groups['label'][3].symbolizers[0].face_name)
        self.assertEqual(10, text_rule_groups['label'][3].symbolizers[0].size)
        self.assertEqual('[foo] >= 1', text_rule_groups['label'][3].filter.text)

    def testStyleRules05(self):
        s = """
            Layer label { text-face-name: 'Helvetica'; text-size: 12; text-fill: #000; }
            Layer[foo<1] label { text-face-name: 'Arial'; }
            Layer[zoom<=10] label { text-size: 10; }
            
            Layer label { shield-face-name: 'Helvetica'; shield-size: 12; shield-file: url('http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png'); }
            Layer[foo>1] label { shield-size: 10; }
            Layer[bar=baz] label { shield-size: 14; }
            Layer[bar=quux] label { shield-size: 16; }
        """
    
        declarations = stylesheet_declarations(s, is_merc=True)
        
        text_rule_groups = get_text_rule_groups(declarations)
        
        self.assertEqual(408560, text_rule_groups['label'][0].maxscale.value)
        self.assertEqual(strings('Arial'), text_rule_groups['label'][0].symbolizers[0].face_name)
        self.assertEqual(12, text_rule_groups['label'][0].symbolizers[0].size)
        self.assertEqual('[foo] < 1', text_rule_groups['label'][0].filter.text)
        
        self.assertEqual(408560, text_rule_groups['label'][1].maxscale.value)
        self.assertEqual(strings('Helvetica'), text_rule_groups['label'][1].symbolizers[0].face_name)
        self.assertEqual(12, text_rule_groups['label'][1].symbolizers[0].size)
        self.assertEqual('[foo] >= 1', text_rule_groups['label'][1].filter.text)
    
        self.assertEqual(408561, text_rule_groups['label'][2].minscale.value)
        self.assertEqual(strings('Arial'), text_rule_groups['label'][2].symbolizers[0].face_name)
        self.assertEqual(10, text_rule_groups['label'][2].symbolizers[0].size)
        self.assertEqual('[foo] < 1', text_rule_groups['label'][2].filter.text)
        
        self.assertEqual(408561, text_rule_groups['label'][3].minscale.value)
        self.assertEqual(strings('Helvetica'), text_rule_groups['label'][3].symbolizers[0].face_name)
        self.assertEqual(10, text_rule_groups['label'][3].symbolizers[0].size)
        self.assertEqual('[foo] >= 1', text_rule_groups['label'][3].filter.text)
        
        shield_rule_groups = get_shield_rule_groups(declarations, self.dirs)
        
        assert shield_rule_groups['label'][0].minscale is None
        assert shield_rule_groups['label'][0].maxscale is None
        self.assertEqual(strings('Helvetica'), shield_rule_groups['label'][0].symbolizers[0].face_name)
        self.assertEqual(12, shield_rule_groups['label'][0].symbolizers[0].size)
        if MAPNIK_VERSION < 701:
            self.assertEqual(8, shield_rule_groups['label'][0].symbolizers[0].width)
            self.assertEqual(8, shield_rule_groups['label'][0].symbolizers[0].height)
        self.assertEqual("not [bar] = 'baz' and not [bar] = 'quux' and [foo] <= 1", shield_rule_groups['label'][0].filter.text)
        
        assert shield_rule_groups['label'][1].minscale is None
        assert shield_rule_groups['label'][1].maxscale is None
        self.assertEqual(strings('Helvetica'), shield_rule_groups['label'][1].symbolizers[0].face_name)
        self.assertEqual(10, shield_rule_groups['label'][1].symbolizers[0].size)
        if MAPNIK_VERSION < 701:
            self.assertEqual(8, shield_rule_groups['label'][1].symbolizers[0].width)
            self.assertEqual(8, shield_rule_groups['label'][1].symbolizers[0].height)
        self.assertEqual("not [bar] = 'baz' and not [bar] = 'quux' and [foo] > 1", shield_rule_groups['label'][1].filter.text)
        
        assert shield_rule_groups['label'][2].minscale is None
        assert shield_rule_groups['label'][2].maxscale is None
        self.assertEqual(strings('Helvetica'), shield_rule_groups['label'][2].symbolizers[0].face_name)
        self.assertEqual(14, shield_rule_groups['label'][2].symbolizers[0].size)
        if MAPNIK_VERSION < 701:
            self.assertEqual(8, shield_rule_groups['label'][2].symbolizers[0].width)
            self.assertEqual(8, shield_rule_groups['label'][2].symbolizers[0].height)
        self.assertEqual("[bar] = 'baz' and [foo] <= 1", shield_rule_groups['label'][2].filter.text)
        
        assert shield_rule_groups['label'][3].minscale is None
        assert shield_rule_groups['label'][3].maxscale is None
        self.assertEqual(strings('Helvetica'), shield_rule_groups['label'][3].symbolizers[0].face_name)
        self.assertEqual(14, shield_rule_groups['label'][3].symbolizers[0].size)
        if MAPNIK_VERSION < 701:
            self.assertEqual(8, shield_rule_groups['label'][3].symbolizers[0].width)
            self.assertEqual(8, shield_rule_groups['label'][3].symbolizers[0].height)
        self.assertEqual("[bar] = 'baz' and [foo] > 1", shield_rule_groups['label'][3].filter.text)
        
        assert shield_rule_groups['label'][4].minscale is None
        assert shield_rule_groups['label'][4].maxscale is None
        self.assertEqual(strings('Helvetica'), shield_rule_groups['label'][4].symbolizers[0].face_name)
        self.assertEqual(16, shield_rule_groups['label'][4].symbolizers[0].size)
        if MAPNIK_VERSION < 701:
            self.assertEqual(8, shield_rule_groups['label'][4].symbolizers[0].width)
            self.assertEqual(8, shield_rule_groups['label'][4].symbolizers[0].height)
        self.assertEqual("[bar] = 'quux' and [foo] <= 1", shield_rule_groups['label'][4].filter.text)
        
        assert shield_rule_groups['label'][5].minscale is None
        assert shield_rule_groups['label'][5].maxscale is None
        self.assertEqual(strings('Helvetica'), shield_rule_groups['label'][5].symbolizers[0].face_name)
        self.assertEqual(16, shield_rule_groups['label'][5].symbolizers[0].size)
        if MAPNIK_VERSION < 701:
            self.assertEqual(8, shield_rule_groups['label'][5].symbolizers[0].width)
            self.assertEqual(8, shield_rule_groups['label'][5].symbolizers[0].height)
        self.assertEqual("[bar] = 'quux' and [foo] > 1", shield_rule_groups['label'][5].filter.text)

    def testStyleRules06(self):
        s = """
            Layer label { shield-face-name: 'Helvetica'; shield-size: 12; shield-file: url('http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png'); }
            Layer[foo>1] label { shield-size: 10; }
            Layer[bar=baz] label { shield-size: 14; }
            Layer[bar=quux] label { shield-size: 16; }
    
            Layer { point-file: url('http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png'); }
        """
    
        declarations = stylesheet_declarations(s, is_merc=True)
        
        shield_rule_groups = get_shield_rule_groups(declarations, self.dirs)
        
        assert shield_rule_groups['label'][0].minscale is None
        assert shield_rule_groups['label'][0].maxscale is None
        self.assertEqual(strings('Helvetica'), shield_rule_groups['label'][0].symbolizers[0].face_name)
        self.assertEqual(12, shield_rule_groups['label'][0].symbolizers[0].size)
        if MAPNIK_VERSION < 701:
            self.assertEqual(8, shield_rule_groups['label'][0].symbolizers[0].width)
            self.assertEqual(8, shield_rule_groups['label'][0].symbolizers[0].height)
        self.assertEqual("not [bar] = 'baz' and not [bar] = 'quux' and [foo] <= 1", shield_rule_groups['label'][0].filter.text)
        
        assert shield_rule_groups['label'][1].minscale is None
        assert shield_rule_groups['label'][1].maxscale is None
        self.assertEqual(strings('Helvetica'), shield_rule_groups['label'][1].symbolizers[0].face_name)
        self.assertEqual(10, shield_rule_groups['label'][1].symbolizers[0].size)
        if MAPNIK_VERSION < 701:
            self.assertEqual(8, shield_rule_groups['label'][1].symbolizers[0].width)
            self.assertEqual(8, shield_rule_groups['label'][1].symbolizers[0].height)
        self.assertEqual("not [bar] = 'baz' and not [bar] = 'quux' and [foo] > 1", shield_rule_groups['label'][1].filter.text)
        
        assert shield_rule_groups['label'][2].minscale is None
        assert shield_rule_groups['label'][2].maxscale is None
        self.assertEqual(strings('Helvetica'), shield_rule_groups['label'][2].symbolizers[0].face_name)
        self.assertEqual(14, shield_rule_groups['label'][2].symbolizers[0].size)
        if MAPNIK_VERSION < 701:
            self.assertEqual(8, shield_rule_groups['label'][2].symbolizers[0].width)
            self.assertEqual(8, shield_rule_groups['label'][2].symbolizers[0].height)
        self.assertEqual("[bar] = 'baz' and [foo] <= 1", shield_rule_groups['label'][2].filter.text)
        
        assert shield_rule_groups['label'][3].minscale is None
        assert shield_rule_groups['label'][3].maxscale is None
        self.assertEqual(strings('Helvetica'), shield_rule_groups['label'][3].symbolizers[0].face_name)
        self.assertEqual(14, shield_rule_groups['label'][3].symbolizers[0].size)
        if MAPNIK_VERSION < 701:
            self.assertEqual(8, shield_rule_groups['label'][3].symbolizers[0].width)
            self.assertEqual(8, shield_rule_groups['label'][3].symbolizers[0].height)
        self.assertEqual("[bar] = 'baz' and [foo] > 1", shield_rule_groups['label'][3].filter.text)
        
        assert shield_rule_groups['label'][4].minscale is None
        assert shield_rule_groups['label'][4].maxscale is None
        self.assertEqual(strings('Helvetica'), shield_rule_groups['label'][4].symbolizers[0].face_name)
        self.assertEqual(16, shield_rule_groups['label'][4].symbolizers[0].size)
        if MAPNIK_VERSION < 701:
            self.assertEqual(8, shield_rule_groups['label'][4].symbolizers[0].width)
            self.assertEqual(8, shield_rule_groups['label'][4].symbolizers[0].height)
        self.assertEqual("[bar] = 'quux' and [foo] <= 1", shield_rule_groups['label'][4].filter.text)
        
        assert shield_rule_groups['label'][5].minscale is None
        assert shield_rule_groups['label'][5].maxscale is None
        self.assertEqual(strings('Helvetica'), shield_rule_groups['label'][5].symbolizers[0].face_name)
        self.assertEqual(16, shield_rule_groups['label'][5].symbolizers[0].size)
        if MAPNIK_VERSION < 701:
            self.assertEqual(8, shield_rule_groups['label'][5].symbolizers[0].width)
            self.assertEqual(8, shield_rule_groups['label'][5].symbolizers[0].height)
        self.assertEqual("[bar] = 'quux' and [foo] > 1", shield_rule_groups['label'][5].filter.text)

        point_rules = get_point_rules(declarations, self.dirs)
        
        assert point_rules[0].filter is None
        assert point_rules[0].minscale is None
        assert point_rules[0].maxscale is None
        if MAPNIK_VERSION < 701:
            self.assertEqual('png', point_rules[0].symbolizers[0].type)
            self.assertEqual(8, point_rules[0].symbolizers[0].width)
            self.assertEqual(8, point_rules[0].symbolizers[0].height)

    def testStyleRules07(self):
        s = """
            Layer { point-file: url('http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png'); }
            Layer { polygon-pattern-file: url('http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png'); }
            Layer { line-pattern-file: url('http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png'); }
        """
    
        declarations = stylesheet_declarations(s, is_merc=True)

        point_rules = get_point_rules(declarations, self.dirs)
        
        assert point_rules[0].filter is None
        assert point_rules[0].minscale is None
        assert point_rules[0].maxscale is None
        if MAPNIK_VERSION < 701:
            self.assertEqual('png', point_rules[0].symbolizers[0].type)
            self.assertEqual(8, point_rules[0].symbolizers[0].width)
            self.assertEqual(8, point_rules[0].symbolizers[0].height)

        polygon_pattern_rules = get_polygon_pattern_rules(declarations, self.dirs)
        
        assert polygon_pattern_rules[0].filter is None
        assert polygon_pattern_rules[0].minscale is None
        assert polygon_pattern_rules[0].maxscale is None
        if MAPNIK_VERSION < 701:
            self.assertEqual('png', polygon_pattern_rules[0].symbolizers[0].type)
            self.assertEqual(8, polygon_pattern_rules[0].symbolizers[0].width)
            self.assertEqual(8, polygon_pattern_rules[0].symbolizers[0].height)

        line_pattern_rules = get_line_pattern_rules(declarations, self.dirs)
        
        assert line_pattern_rules[0].filter is None
        assert line_pattern_rules[0].minscale is None
        assert line_pattern_rules[0].maxscale is None
        if MAPNIK_VERSION < 701:
            self.assertEqual('png', line_pattern_rules[0].symbolizers[0].type)
            self.assertEqual(8, line_pattern_rules[0].symbolizers[0].width)
            self.assertEqual(8, line_pattern_rules[0].symbolizers[0].height)

    def testStyleRules08(self):
        s = """
            Layer { line-width: 3; line-color: #fff; }
            Layer[foo=1] { outline-width: 1; outline-color: #000; }
            Layer[bar=1] { inline-width: 1; inline-color: #999; }
        """
    
        declarations = stylesheet_declarations(s, is_merc=True)
        
        line_rules = get_line_rules(declarations)
        
        self.assertEqual(4, len(line_rules))
        
    
        assert line_rules[0].minscale is None
        assert line_rules[0].maxscale is None
        self.assertEqual("not [bar] = 1 and not [foo] = 1", line_rules[0].filter.text)
        self.assertEqual(1, len(line_rules[0].symbolizers))
        
        line_symbolizer = line_rules[0].symbolizers[0]
        self.assertEqual(color(0xFF, 0xFF, 0xFF), line_symbolizer.color)
        self.assertEqual(3.0, line_symbolizer.width)
        
    
        assert line_rules[1].minscale is None
        assert line_rules[1].maxscale is None
        self.assertEqual("not [bar] = 1 and [foo] = 1", line_rules[1].filter.text)
        self.assertEqual(2, len(line_rules[1].symbolizers))
        
        outline_symbolizer = line_rules[1].symbolizers[0]
        self.assertEqual(color(0x00, 0x00, 0x00), outline_symbolizer.color)
        self.assertEqual(5.0, outline_symbolizer.width)
        
        line_symbolizer = line_rules[1].symbolizers[1]
        self.assertEqual(color(0xff, 0xff, 0xff), line_symbolizer.color)
        self.assertEqual(3.0, line_symbolizer.width)
    
    
        assert line_rules[2].minscale is None
        assert line_rules[2].maxscale is None
        self.assertEqual("[bar] = 1 and not [foo] = 1", line_rules[2].filter.text)
        self.assertEqual(2, len(line_rules[2].symbolizers))
        
        line_symbolizer = line_rules[2].symbolizers[0]
        self.assertEqual(color(0xff, 0xff, 0xff), line_symbolizer.color)
        self.assertEqual(3.0, line_symbolizer.width)
        
        inline_symbolizer = line_rules[2].symbolizers[1]
        self.assertEqual(color(0x99, 0x99, 0x99), inline_symbolizer.color)
        self.assertEqual(1.0, inline_symbolizer.width)
        
    
        assert line_rules[3].minscale is None
        assert line_rules[3].maxscale is None
        self.assertEqual("[bar] = 1 and [foo] = 1", line_rules[3].filter.text)
        self.assertEqual(3, len(line_rules[3].symbolizers))
        
        outline_symbolizer = line_rules[3].symbolizers[0]
        self.assertEqual(color(0x00, 0x00, 0x00), outline_symbolizer.color)
        self.assertEqual(5.0, outline_symbolizer.width)
        
        line_symbolizer = line_rules[3].symbolizers[1]
        self.assertEqual(color(0xff, 0xff, 0xff), line_symbolizer.color)
        self.assertEqual(3.0, line_symbolizer.width)
        
        inline_symbolizer = line_rules[3].symbolizers[2]
        self.assertEqual(color(0x99, 0x99, 0x99), inline_symbolizer.color)
        self.assertEqual(1.0, inline_symbolizer.width)

    def testStyleRules09(self):
        s = """
            Layer { line-color: #000; }
            
            Layer[ELEVATION=0] { line-width: 1; }
            Layer[ELEVATION=50] { line-width: 2; }
            Layer[ELEVATION>900] { line-width: 3; line-color: #fff; }
        """
    
        declarations = stylesheet_declarations(s, is_merc=True)
        
        line_rules = get_line_rules(declarations)
        
        self.assertEqual('[ELEVATION] = 0', line_rules[0].filter.text)
        self.assertEqual(color(0x00, 0x00, 0x00), line_rules[0].symbolizers[0].color)
        self.assertEqual(1.0, line_rules[0].symbolizers[0].width)
    
        self.assertEqual('[ELEVATION] = 50', line_rules[1].filter.text)
        self.assertEqual(color(0x00, 0x00, 0x00), line_rules[1].symbolizers[0].color)
        self.assertEqual(2.0, line_rules[1].symbolizers[0].width)
    
        self.assertEqual('[ELEVATION] > 900', line_rules[2].filter.text)
        self.assertEqual(color(0xFF, 0xFF, 0xFF), line_rules[2].symbolizers[0].color)
        self.assertEqual(3.0, line_rules[2].symbolizers[0].width)

    def testStyleRules10(self):
        s = """
            Layer[landuse!=desert] { polygon-fill: #006; }
            Layer[landuse=field] { polygon-fill: #001; }
            Layer[landuse=meadow] { polygon-fill: #002; }
            Layer[landuse=forest] { polygon-fill: #003; }
            Layer[landuse=woods] { polygon-fill: #004; }
            Layer { polygon-fill: #000; }
        """
    
        declarations = stylesheet_declarations(s, is_merc=True)
        
        polygon_rules = get_polygon_rules(declarations)
        
        self.assertEqual("not [landuse] = 'field' and not [landuse] = 'woods' and not [landuse] = 'desert' and not [landuse] = 'forest' and not [landuse] = 'meadow'", polygon_rules[0].filter.text)
        self.assertEqual(color(0x00, 0x00, 0x66), polygon_rules[0].symbolizers[0].color)
        
        self.assertEqual("[landuse] = 'desert'", polygon_rules[1].filter.text)
        self.assertEqual(color(0x00, 0x00, 0x00), polygon_rules[1].symbolizers[0].color)
        
        self.assertEqual("[landuse] = 'field'", polygon_rules[2].filter.text)
        self.assertEqual(color(0x00, 0x00, 0x11), polygon_rules[2].symbolizers[0].color)
        
        self.assertEqual("[landuse] = 'forest'", polygon_rules[3].filter.text)
        self.assertEqual(color(0x00, 0x00, 0x33), polygon_rules[3].symbolizers[0].color)
        
        self.assertEqual("[landuse] = 'meadow'", polygon_rules[4].filter.text)
        self.assertEqual(color(0x00, 0x00, 0x22), polygon_rules[4].symbolizers[0].color)
        
        self.assertEqual("[landuse] = 'woods'", polygon_rules[5].filter.text)
        self.assertEqual(color(0x00, 0x00, 0x44), polygon_rules[5].symbolizers[0].color)

    def testStyleRules11(self):
        """ Spaces and negative numbers in attribute selectors need to be acceptable
        """
        s = """
            Layer[PERSONS < -2000000] { polygon-fill: #6CAE4C; }
            Layer[PERSONS >= -2000000][PERSONS < 4000000] { polygon-fill: #3B7AB3; }
            Layer[PERSONS > 4000000] { polygon-fill: #88000F; }
        """
    
        declarations = stylesheet_declarations(s, False)
        polygon_rules = get_polygon_rules(declarations)
        
        self.assertEqual("[PERSONS] < -2000000", polygon_rules[0].filter.text)
        self.assertEqual(color(0x6c, 0xae, 0x4c), polygon_rules[0].symbolizers[0].color)
        
        self.assertEqual("[PERSONS] >= -2000000 and [PERSONS] < 4000000", polygon_rules[1].filter.text)
        self.assertEqual(color(0x3b, 0x7a, 0xb3), polygon_rules[1].symbolizers[0].color)
        
        self.assertEqual("[PERSONS] > 4000000", polygon_rules[2].filter.text)
        self.assertEqual(color(0x88, 0x00, 0x0f), polygon_rules[2].symbolizers[0].color)

    def testStyleRules11b(self):
        s = """
            Layer
            {
                polygon-fill: #000;
                polygon-opacity: .5;

                line-color: #000;
                line-width: 2;
                line-opacity: .5;
                line-join: miter;
                line-cap: butt;
                line-dasharray: 1,2,3;
            }
        """

        declarations = stylesheet_declarations(s, is_merc=True)

        polygon_rules = get_polygon_rules(declarations)
        
        self.assertEqual(color(0x00, 0x00, 0x00), polygon_rules[0].symbolizers[0].color)
        self.assertEqual(0.5, polygon_rules[0].symbolizers[0].opacity)

        line_rules = get_line_rules(declarations)
        
        self.assertEqual(color(0x00, 0x00, 0x00), line_rules[0].symbolizers[0].color)
        self.assertEqual(2.0, line_rules[0].symbolizers[0].width)
        self.assertEqual(0.5, line_rules[0].symbolizers[0].opacity)
        self.assertEqual('miter', line_rules[0].symbolizers[0].join)
        self.assertEqual('butt', line_rules[0].symbolizers[0].cap)
        self.assertEqual(numbers(1, 2, 3), line_rules[0].symbolizers[0].dashes)

    def testStyleRules12(self):
        s = """
            Layer label
            {
                text-face-name: 'Helvetica';
                text-size: 12;
                
                text-fill: #f00;
                text-wrap-width: 100;
                text-spacing: 50;
                text-label-position-tolerance: 25;
                text-max-char-angle-delta: 10;
                text-halo-fill: #ff0;
                text-halo-radius: 2;
                text-dx: 10;
                text-dy: 15;
                text-avoid-edges: true;
                text-min-distance: 5;
                text-allow-overlap: false;
                text-placement: point;
            }
        """

        declarations = stylesheet_declarations(s, is_merc=True)

        text_rule_groups = get_text_rule_groups(declarations)
        
        self.assertEqual(strings('Helvetica'), text_rule_groups['label'][0].symbolizers[0].face_name)
        self.assertEqual(strings('Helvetica'), text_rule_groups['label'][0].symbolizers[0].face_name)
        self.assertEqual(12, text_rule_groups['label'][0].symbolizers[0].size)

        self.assertEqual(color(0xFF, 0x00, 0x00), text_rule_groups['label'][0].symbolizers[0].color)
        self.assertEqual(100, text_rule_groups['label'][0].symbolizers[0].wrap_width)
        self.assertEqual(50, text_rule_groups['label'][0].symbolizers[0].label_spacing)
        self.assertEqual(25, text_rule_groups['label'][0].symbolizers[0].label_position_tolerance)
        self.assertEqual(10, text_rule_groups['label'][0].symbolizers[0].max_char_angle_delta)
        self.assertEqual(color(0xFF, 0xFF, 0x00), text_rule_groups['label'][0].symbolizers[0].halo_color)
        self.assertEqual(2, text_rule_groups['label'][0].symbolizers[0].halo_radius)
        self.assertEqual(10, text_rule_groups['label'][0].symbolizers[0].dx)
        self.assertEqual(15, text_rule_groups['label'][0].symbolizers[0].dy)
        self.assertEqual(boolean(1), text_rule_groups['label'][0].symbolizers[0].avoid_edges)
        self.assertEqual(5, text_rule_groups['label'][0].symbolizers[0].minimum_distance)
        self.assertEqual(boolean(0), text_rule_groups['label'][0].symbolizers[0].allow_overlap)
        self.assertEqual('point', text_rule_groups['label'][0].symbolizers[0].label_placement)

    def testStyleRules12a(self):
        s = """
            Layer label1
            {
                text-face-name: 'Bananas';
                text-size: 12;
                text-fill: #f00;
            }
            Layer label2
            {
                text-face-name: "Monkeys";
                text-size: 12;
                text-fill: #f00;
            }
        """

        declarations = stylesheet_declarations(s, is_merc=True)

        text_rule_groups = get_text_rule_groups(declarations)
        
        self.assertEqual(strings('Bananas'), text_rule_groups['label1'][0].symbolizers[0].face_name)
        self.assertEqual(strings('Monkeys'), text_rule_groups['label2'][0].symbolizers[0].face_name)

    def testStyleRules13(self):
        s = """
            Layer
            {
                point-file: url('http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png');
                point-width: 16;
                point-height: 16;
                point-allow-overlap: true;

                polygon-pattern-file: url('http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png');
                polygon-pattern-width: 16;
                polygon-pattern-height: 16;

                line-pattern-file: url('http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png');
                line-pattern-width: 16;
                line-pattern-height: 16;
            }
        """

        declarations = stylesheet_declarations(s, is_merc=True)

        point_rules = get_point_rules(declarations, self.dirs)
        
        self.assertEqual(16, point_rules[0].symbolizers[0].width)
        self.assertEqual(16, point_rules[0].symbolizers[0].height)
        self.assertEqual(boolean(True), point_rules[0].symbolizers[0].allow_overlap)

        polygon_pattern_rules = get_polygon_pattern_rules(declarations, self.dirs)
        
        self.assertEqual(16, polygon_pattern_rules[0].symbolizers[0].width)
        self.assertEqual(16, polygon_pattern_rules[0].symbolizers[0].height)

        line_pattern_rules = get_line_pattern_rules(declarations, self.dirs)
        
        self.assertEqual(16, line_pattern_rules[0].symbolizers[0].width)
        self.assertEqual(16, line_pattern_rules[0].symbolizers[0].height)

    def testStyleRules14(self):
        s = """
            Layer just_image
            {
                shield-file: url('http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png');
                shield-width: 16;
                shield-height: 16;
                
                shield-min-distance: 5;
            }

            Layer both
            {
                shield-face-name: 'Interstate';
                shield-size: 12;
                
                shield-file: url('http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png');
                shield-width: 16;
                shield-height: 16;
                
                shield-fill: #f00;
                shield-min-distance: 5;
            }
        """

        declarations = stylesheet_declarations(s, is_merc=True)

        shield_rule_groups = get_shield_rule_groups(declarations, self.dirs)
        
        # Also Mapnik's python bindings should be able to allow a ShieldSymbolizer without text
        # put this is not properly exposed in the latest release (0.7.1)
        # So, disabling this test until we actually add support in Mapnik 0.7.x
        # http://trac.mapnik.org/ticket/652
        #self.assertEqual(16, shield_rule_groups['just_image'][0].symbolizers[0].width)
        #self.assertEqual(16, shield_rule_groups['just_image'][0].symbolizers[0].height)
        #self.assertEqual(5, shield_rule_groups['just_image'][0].symbolizers[0].minimum_distance)
        
        self.assertEqual(strings('Interstate'), shield_rule_groups['both'][0].symbolizers[0].face_name)
        self.assertEqual(12, shield_rule_groups['both'][0].symbolizers[0].size)
        self.assertEqual(color(0xFF, 0x00, 0x00), shield_rule_groups['both'][0].symbolizers[0].color)
        self.assertEqual(16, shield_rule_groups['both'][0].symbolizers[0].width)
        self.assertEqual(16, shield_rule_groups['both'][0].symbolizers[0].height)
        self.assertEqual(5, shield_rule_groups['both'][0].symbolizers[0].minimum_distance)

class DataSourcesTests(unittest.TestCase):

    def gen_section(self, name, **kwargs):
        return """[%s]\n%s\n""" % (name, "\n".join(("%s=%s" % kwarg for kwarg in kwargs.items())))

    def testSimple1(self):
        cdata = """
[simple]
type=shape
file=foo.shp
garbage=junk
"""
        dss = DataSources(None, None)
        dss.add_config(cdata, __file__)
        self.assertTrue(dss.sources['simple'] != None)

        ds = dss.sources['simple']
        self.assertTrue(ds['parameters'] != None)
        p = ds['parameters']
        self.assertEqual(p['type'],'shape')
        self.assertEqual(p['file'],'foo.shp')
        self.assertTrue(p.get('garbage') == None)

        self.assertRaises(Exception, dss.add_config, (self.gen_section("foo", encoding="bar"), __file__))
    
    def testChain1(self):
        dss = DataSources(None, None)
        dss.add_config(self.gen_section("t1", type="shape", file="foo"), __file__)
        dss.add_config(self.gen_section("t2", type="shape", file="foo"), __file__)
        self.assertTrue(dss.get('t1') != None)
        self.assertTrue(dss.get('t2') != None)

    def testDefaults1(self):
        dss = DataSources(None, None)
        sect = self.gen_section("DEFAULT", var="cows") + "\n" + self.gen_section("t1", type="shape", file="%(var)s") 
        #dss.add_config(self.gen_section("DEFAULT", var="cows"), __file__)
        #dss.add_config(self.gen_section("t1", type="shape", file="%(var)s"), __file__)
        dss.add_config(sect, __file__)

        self.assertEqual(dss.get('t1')['parameters']['file'], "cows")

    def testLocalDefaultsFromString(self):
        dss = DataSources(None, None)
        dss.set_local_cfg_data(self.gen_section("DEFAULT", var="cows2"))
        sect = self.gen_section("DEFAULT", var="cows") + "\n" + self.gen_section("t1", type="shape", file="%(var)s") 
        dss.add_config(sect, __file__)
        dss.finalize()
        self.assertEqual(dss.get('t1')['parameters']['file'], "cows2")

    def testLocalDefaultsFromFile(self):
        handle, cfgpath = tempfile.mkstemp()
        os.close(handle)

        try:
            open(cfgpath, 'w').write(self.gen_section("DEFAULT", var="cows2"))
            self.assertTrue(os.path.exists(cfgpath))
            dss = DataSources(__file__, cfgpath)
            sect = self.gen_section("DEFAULT", var="cows") + "\n" + self.gen_section("t1", type="shape", file="%(var)s") 
            dss.add_config(sect, __file__)
            self.assertEqual(dss.get('t1')['parameters']['file'], "cows2")
        finally:
            os.unlink(cfgpath)

    def testBase1(self):
        dss = DataSources(None, None)
        dss.add_config(self.gen_section("base", type="shape", encoding="latin1"), __file__)
        dss.add_config(self.gen_section("t2", template="base", file="foo"), __file__)
        self.assertTrue("base" in dss.templates)
        self.assertEqual(dss.get('t2')['template'], 'base')
        self.assertEqual(dss.get('t2')['parameters']['file'], 'foo')

    def testSRS(self):
        dss = DataSources(None, None)
        dss.add_config(self.gen_section("s", type="shape", layer_srs="epsg:4326"), __file__)
        dss.add_config(self.gen_section("g", type="shape", layer_srs="epsg:900913"), __file__)
        self.assertEqual(dss.get("s")['layer_srs'], dss.PROJ4_PROJECTIONS['epsg:4326'])
        self.assertEqual(dss.get("g")['layer_srs'], dss.PROJ4_PROJECTIONS['epsg:900913'])
        self.assertRaises(Exception, dss.add_config, (self.gen_section("s", type="shape", layer_srs="epsg:43223432423"), __file__))

    def testDataTypes(self):
        dss = DataSources(None, None)
        dss.add_config(self.gen_section("s",
                                        type="postgis",
                                        cursor_size="5",
                                        estimate_extent="yes"), __file__)
        self.assertEqual(dss.get("s")['parameters']['cursor_size'], 5)
        self.assertEqual(dss.get("s")['parameters']['estimate_extent'], True)

        self.assertRaises(Exception,
                          dss.add_config,
                          (self.gen_section("f",
                                            type="postgis",
                                            cursor_size="5.xx",
                                            estimate_extent="yes"), __file__))


class CompileXMLTests(unittest.TestCase):

    def setUp(self):
        # a directory for all the temp files to be created below
        self.tmpdir = tempfile.mkdtemp(prefix='cascadenik-tests-')
        self.data = tempfile.mkdtemp(prefix='cascadenik-data-')
        self.dirs = Directories(self.tmpdir, self.tmpdir, os.getcwd())
        
        for name in ('test.dbf', 'test.prj', 'test.qpj', 'test.shp', 'test.shx'):
            href = 'http://cascadenik-sampledata.s3.amazonaws.com/data/' + name
            path = os.path.join(self.data, name)
            
            file = open(path, 'w')
            file.write(urllib.urlopen(href).read())
            file.close()
        
    def tearDown(self):
        # destroy the above-created directory
        shutil.rmtree(self.tmpdir)
        shutil.rmtree(self.data)

    def testCompile1(self):
        """
        """
        s = """<?xml version="1.0"?>
            <Map>
                <Stylesheet>
                    Map { map-bgcolor: #fff; }
                    
                    Layer
                    {
                        polygon-fill: #999;
                        line-color: #fff;
                        line-width: 1;
                        outline-color: #000;
                        outline-width: 1;
                    }
                    
                    Layer name
                    {
                        text-face-name: 'Comic Sans';
                        text-size: 14;
                        text-fill: #f90;
                    }
                </Stylesheet>
                <Datasource name="template">
                    <Parameter name="type">shape</Parameter>
                    <Parameter name="encoding">latin1</Parameter>
                    <Parameter name="base">data</Parameter>
                </Datasource>
                <Layer srs="+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs">
                    <Datasource base="template">
                        <Parameter name="file">test.shp</Parameter>
                    </Datasource>
                </Layer>
                <Layer srs="+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs">
                    <Datasource base="template">
                        <Parameter name="file">test.shp</Parameter>
                    </Datasource>
                </Layer>
            </Map>
        """
        self.doCompile1(s)

        # run the same test with a datasourcesconfig
        dscfg = """<?xml version="1.0"?>
            <Map>
                <Stylesheet>
                    Map { map-bgcolor: #fff; }
                    
                    Layer
                    {
                        polygon-fill: #999;
                        line-color: #fff;
                        line-width: 1;
                        outline-color: #000;
                        outline-width: 1;
                    }
                    
                    Layer name
                    {
                        text-face-name: 'Comic Sans';
                        text-size: 14;
                        text-fill: #f90;
                    }
                </Stylesheet>
                <DataSourcesConfig>
[DEFAULT]
default_layer_srs = epsg:4326
other_srs = epsg:4326

[template1]
type=shape
layer_srs=%(default_layer_srs)s
encoding=latin1
base=data

[test_shp]
file=test.shp
template=template1

[test_shp_2]
type=shape
encoding=latin1
base=data
layer_srs=%(other_srs)s
                </DataSourcesConfig>
                <Layer source_name="test_shp" />
                <Layer source_name="test_shp_2" />
            </Map>
        """
        map = self.doCompile1(dscfg)        
        self.assertEqual(map.layers[1].srs, '+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs')
        
        handle, cfgpath = tempfile.mkstemp()
        os.close(handle)

        try:
            open(cfgpath, 'w').write("[DEFAULT]\nother_srs=epsg:900913")
            map = self.doCompile1(dscfg, datasources_cfg=cfgpath)
            self.assertEqual(map.layers[1].srs, '+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext  +no_defs')
        finally:
            os.unlink(cfgpath)
        
    def doCompile1(self, s, **kwargs):
        map = compile(s, self.dirs, **kwargs)
        
        self.assertEqual(2, len(map.layers))
        self.assertEqual(3, len(map.layers[0].styles))

        self.assertEqual(1, len(map.layers[0].styles[0].rules))
        self.assertEqual(1, len(map.layers[0].styles[0].rules[0].symbolizers))

        self.assertEqual(color(0x99, 0x99, 0x99), map.layers[0].styles[0].rules[0].symbolizers[0].color)
        self.assertEqual(1.0, map.layers[0].styles[0].rules[0].symbolizers[0].opacity)

        self.assertEqual(1, len(map.layers[0].styles[1].rules))
        self.assertEqual(2, len(map.layers[0].styles[1].rules[0].symbolizers))

        self.assertEqual(color(0x00, 0x00, 0x00), map.layers[0].styles[1].rules[0].symbolizers[0].color)
        self.assertEqual(color(0xFF, 0xFF, 0xFF), map.layers[0].styles[1].rules[0].symbolizers[1].color)
        self.assertEqual(3.0, map.layers[0].styles[1].rules[0].symbolizers[0].width)
        self.assertEqual(1.0, map.layers[0].styles[1].rules[0].symbolizers[1].width)

        self.assertEqual(1, len(map.layers[0].styles[2].rules))
        self.assertEqual(1, len(map.layers[0].styles[2].rules[0].symbolizers))

        self.assertEqual(strings('Comic Sans'), map.layers[0].styles[2].rules[0].symbolizers[0].face_name)
        self.assertEqual(14, map.layers[0].styles[2].rules[0].symbolizers[0].size)

        self.assertEqual(map.layers[0].srs, '+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs')
        self.assertEqual(os.path.basename(map.layers[0].datasource.parameters['file']), 'test.shp')
        self.assertEqual(map.layers[0].datasource.parameters['encoding'], 'latin1')
        self.assertEqual(map.layers[0].datasource.parameters['type'], 'shape')
        return map

    def testCompile2(self):
        """
        """
        s = """<?xml version="1.0"?>
            <Map>
                <Stylesheet>
                    Map { map-bgcolor: #fff; }
                    
                    Layer
                    {
                        polygon-fill: #999;
                        polygon-opacity: 0.5;
                        line-color: #fff;
                        line-width: 2;
                        outline-color: #000;
                        outline-width: 1;
                    }
                    
                    Layer name
                    {
                        text-face-name: 'Comic Sans';
                        text-size: 14;
                        text-fill: #f90;
                    }
                </Stylesheet>
                <Datasource name="template">
                     <Parameter name="type">shape</Parameter>
                     <Parameter name="encoding">latin1</Parameter>
                </Datasource>

                <Layer>
                    <Datasource base="template">
                        <Parameter name="type">shape</Parameter>
                        <Parameter name="file">%(data)s/test.shp</Parameter>
                    </Datasource>
                </Layer>
            </Map>
        """ % self.__dict__

        map = compile(s, self.dirs)
        
        mmap = mapnik.Map(640, 480)
        map.to_mapnik(mmap)
        
        (handle, path) = tempfile.mkstemp(suffix='.xml', prefix='cascadenik-mapnik-')
        os.close(handle)
        
        mapnik.save_map(mmap, path)
        doc = xml.etree.ElementTree.parse(path)
        map_el = doc.getroot()
        
        #print open(path, 'r').read()
        os.unlink(path)

        self.assertEqual(3, len(map_el.findall('Style')))
        self.assertEqual(1, len(map_el.findall('Layer')))
        self.assertEqual(3, len(map_el.find('Layer').findall('StyleName')))
        
        for stylename_el in map_el.find('Layer').findall('StyleName'):
            self.assertTrue(stylename_el.text in [style_el.get('name') for style_el in map_el.findall('Style')])

        for style_el in map_el.findall('Style'):
            if style_el.get('name').startswith('polygon style '):
                self.assertEqual(1, len(style_el.find('Rule').findall('PolygonSymbolizer')))

            if style_el.get('name').startswith('line style '):
                self.assertEqual(2, len(style_el.find('Rule').findall('LineSymbolizer')))

            if style_el.get('name').startswith('text style '):
                self.assertEqual(1, len(style_el.find('Rule').findall('TextSymbolizer')))

        self.assertEqual(len(map_el.find("Layer").findall('Datasource')), 1)
        params = dict(((p.get('name'), p.text) for p in map_el.find('Layer').find('Datasource').findall('Parameter')))
        self.assertEqual(params['type'], 'shape')
        self.assertTrue(params['file'].endswith('%s/test.shp' % self.data))
        self.assertEqual(params['encoding'], 'latin1')

    def testCompile3(self):
        """
        """
        map = output.Map(layers=[
            output.Layer('this',
            output.Datasource(type="shape",file="%s/test.shp" % self.data), [
                output.Style('a style', [
                    output.Rule(
                        output.MinScaleDenominator(1),
                        output.MaxScaleDenominator(100),
                        output.Filter("[this] = 'that'"),
                        [
                            output.PolygonSymbolizer(color(0xCC, 0xCC, 0xCC))
                        ])
                    ])
                ]),
            output.Layer('that',
            output.Datasource(type="shape",file="%s/test.shp" % self.data), [
                output.Style('another style', [
                    output.Rule(
                        output.MinScaleDenominator(101),
                        output.MaxScaleDenominator(200),
                        output.Filter("[this] = 2"),
                        [
                            output.PolygonSymbolizer(color(0x33, 0x33, 0x33)),
                            output.LineSymbolizer(color(0x66, 0x66, 0x66), 2)
                        ])
                    ])
                ])
            ])
        
        mmap = mapnik.Map(640, 480)
        map.to_mapnik(mmap)
        
        (handle, path) = tempfile.mkstemp(suffix='.xml', prefix='cascadenik-mapnik-')
        os.close(handle)
        
        mapnik.save_map(mmap, path)
        doc = xml.etree.ElementTree.parse(path)
        map_el = doc.getroot()
        
        # print open(path, 'r').read()
        os.unlink(path)
        
        self.assertEqual(2, len(map_el.findall('Style')))
        self.assertEqual(2, len(map_el.findall('Layer')))
        
        for layer_el in map_el.findall('Layer'):
            self.assertEqual(1, len(layer_el.findall('StyleName')))
            self.assertTrue(layer_el.find('StyleName').text in [style_el.get('name') for style_el in map_el.findall('Style')])

        for style_el in map_el.findall('Style'):
            if style_el.get('name') == 'a style':
                self.assertEqual("([this]='that')", style_el.find('Rule').find('Filter').text)
                self.assertEqual('1', style_el.find('Rule').find('MinScaleDenominator').text)
                self.assertEqual('100', style_el.find('Rule').find('MaxScaleDenominator').text)
                self.assertEqual(1, len(style_el.find('Rule').findall('PolygonSymbolizer')))

            if style_el.get('name') == 'another style':
                self.assertEqual('([this]=2)', style_el.find('Rule').find('Filter').text)
                self.assertEqual('101', style_el.find('Rule').find('MinScaleDenominator').text)
                self.assertEqual('200', style_el.find('Rule').find('MaxScaleDenominator').text)
                self.assertEqual(1, len(style_el.find('Rule').findall('PolygonSymbolizer')))
                self.assertEqual(1, len(style_el.find('Rule').findall('LineSymbolizer')))

    def testCompile4(self):
        s = """<?xml version="1.0"?>
            <Map>
                <Stylesheet>
                    Map { 
                        map-bgcolor: #fff; 
                    }
                    
                    Layer {
                        point-file: url('http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png');
                        point-allow-overlap: true;
                    }
                    
                    Layer {
                        line-color: #0f0;
                        line-width: 3;
                        line-dasharray: 8,100,4,50;
                    }

                    Layer { 
                        polygon-pattern-file: url('http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png'); 
                    }
                    Layer { 
                        line-pattern-file: url('http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png'); 
                    }
                    
                    Layer name {
                        text-face-name: "DejaVu Sans Book";
                        text-size: 10;
                        text-fill: #005;
                        text-halo-radius: 1;
                        text-halo-fill: #f00;
                        text-placement: line;
                        text-allow-overlap: true;
                        text-avoid-edges: true;
                    }
                    
                    Layer name2 {
                        shield-face-name: 'Helvetica';
                        shield-size: 12;
                        
                        shield-file: url('http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png');
                        shield-width: 16;
                        shield-height: 16;
                        
                        shield-fill: #f00;
                        shield-min-distance: 5;
                        shield-spacing: 7;
                        shield-line-spacing: 3;
                        shield-character-spacing: 18;
                    }
                </Stylesheet>
                <Datasource name="template">
                     <Parameter name="type">shape</Parameter>
                     <Parameter name="encoding">latin1</Parameter>
                </Datasource>

                <Layer>
                    <Datasource base="template">
                        <Parameter name="type">shape</Parameter>
                        <Parameter name="file">%(data)s/test.shp</Parameter>
                    </Datasource>
                </Layer>
            </Map>
        """ % self.__dict__

        mmap = mapnik.Map(640, 480)
        ms = compile(s, self.dirs)
        ms.to_mapnik(mmap, self.dirs)
        mapnik.save_map(mmap, os.path.join(self.tmpdir, 'out.mml'))

    def testCompile5(self):
        s = u"""<?xml version="1.0" encoding="UTF-8" ?>
            <Map>
                <Stylesheet>
                    Layer[name="Grüner Strich"] { polygon-fill: #000; }
                </Stylesheet>
                <Layer>
                    <Datasource>
                        <Parameter name="type">shape</Parameter>
                        <Parameter name="file">%(data)s/test.shp</Parameter>
                    </Datasource>
                </Layer>
            </Map>
        """.encode('utf-8') % self.__dict__

        mmap = mapnik.Map(640, 480)
        ms = compile(s, self.dirs)
        ms.to_mapnik(mmap, self.dirs)
        mapnik.save_map(mmap, os.path.join(self.tmpdir, 'out.mml'))


    def testCompile6(self):
        s = u"""
            Layer NAME
            {
                text-anchor-dx: 10;
                text-anchor-dy: 10;
                text-allow-overlap: true;
                text-avoid-edges: true;
                text-align: middle;
                text-character-spacing: 10;
                text-dx: 10;
                text-dy: 15;
                text-face-name: 'Helvetica';
                text-fill: #f00;
                text-force-odd-labels: true;
                text-halo-fill: #ff0;
                text-halo-radius: 2;
                text-label-position-tolerance: 25;
                text-line-spacing:10;
                
                text-anchor-dx: 10;
                text-anchor-dy: 10;
                text-align: left;
                text-vertical-align: bottom;
                text-justify-align: left;
                text-transform: uppercase;
                text-size: 12;
                text-spacing: 50;
                text-wrap-width: 100;
                text-transform: uppercase;
                text-max-char-angle-delta: 10;
                text-min-distance: 5;
                text-placement: line;
                text-vertical-align: top;
            }
        """
        declarations = stylesheet_declarations(s, is_merc=True)
        text_rule_groups = get_text_rule_groups(declarations)
        sym = text_rule_groups['NAME'][0].symbolizers[0].to_mapnik()
        
        if MAPNIK_VERSION >= 200000:
            self.assertEqual((10, 15), sym.properties.displacement if (MAPNIK_VERSION >= 200100) else sym.displacement)
        else:
            self.assertEqual([10, 15], sym.get_displacement())
        
        # todo - anchor (does not do anything yet in mapnik, but likely will)
        # and is not set in xml, but accepted in python
        #self.assertEqual([0,5], sym.get_anchor())
        self.assertEqual(True, sym.properties.allow_overlap if (MAPNIK_VERSION >= 200100) else sym.allow_overlap)
        self.assertEqual(True, sym.properties.avoid_edges if (MAPNIK_VERSION >= 200100) else sym.avoid_edges)
        self.assertEqual(10, sym.format.character_spacing if (MAPNIK_VERSION >= 200100) else sym.character_spacing)
        self.assertEqual('Helvetica', sym.format.face_name if (MAPNIK_VERSION >= 200100) else sym.face_name)
        self.assertEqual(mapnik.Color("#f00"), sym.format.fill if (MAPNIK_VERSION >= 200100) else sym.fill)
        
        self.assertEqual(True, sym.properties.force_odd_labels if (MAPNIK_VERSION >= 200100) else sym.force_odd_labels)
        self.assertEqual(mapnik.justify_alignment.LEFT, sym.properties.justify_alignment if (MAPNIK_VERSION >= 200100) else sym.justify_alignment)
        self.assertEqual(mapnik.Color("#ff0"), sym.format.halo_fill if (MAPNIK_VERSION >= 200100) else sym.halo_fill)
        self.assertEqual(2, sym.format.halo_radius if (MAPNIK_VERSION >= 200100) else sym.halo_radius)
        
        if MAPNIK_VERSION >= 200100:
            # TextSymbolizer lost its "name" attribute in Mapnik 2.1.
            pass
        elif MAPNIK_VERSION >= 200001:
            self.assertEqual('[NAME]', str(sym.name))
        else:
            self.assertEqual('NAME', sym.name)
        
        self.assertEqual(12, sym.format.text_size if (MAPNIK_VERSION >= 200100) else sym.text_size)
        self.assertEqual(100, sym.properties.wrap_width if (MAPNIK_VERSION >= 200100) else sym.wrap_width)
        self.assertEqual(50, sym.properties.label_spacing if (MAPNIK_VERSION >= 200100) else sym.label_spacing)
        self.assertEqual(25, sym.properties.label_position_tolerance if (MAPNIK_VERSION >= 200100) else sym.label_position_tolerance)
        
        if MAPNIK_VERSION >= 200100:
            # Seriously?
            self.assertEqual(10, sym.properties.maximum_angle_char_delta if (MAPNIK_VERSION >= 200100) else sym.maximum_angle_char_delta)
        else:
            self.assertEqual(10, sym.max_char_angle_delta)
        
        self.assertEqual(10, sym.format.line_spacing if (MAPNIK_VERSION >= 200100) else sym.line_spacing)
        self.assertEqual(5, sym.properties.minimum_distance if (MAPNIK_VERSION >= 200100) else sym.minimum_distance)
        self.assertEqual(mapnik.label_placement.LINE_PLACEMENT, sym.properties.label_placement if (MAPNIK_VERSION >= 200100) else sym.label_placement)
    
    def testCompile7(self):
        s = """
            #roads
            {
                line-color: #f90;
                line-width: 1 !important;
            }
            
            #roads[tiny=yes]
            {
                display: none;
            }
        """
        declarations = stylesheet_declarations(s, is_merc=True)
        line_rules = get_line_rules(declarations)
        
        self.assertEqual(1, len(line_rules))
        self.assertEqual(line_rules[0].filter.text, "not [tiny] = 'yes'")

    def testCompile8(self):
        s = """
            #roads[zoom=12]
            {
                line-color: #f90;
                line-width: 1;
            }

            #roads[zoom=12] name
            {
                text-fill: #f90;
                text-face-name: "Courier New";
                text-size: 12;
            }
        """
        declarations = stylesheet_declarations(s, is_merc=True, scale=2)

        line_rules = get_line_rules(declarations)
        line_rule = line_rules[0]
        
        self.assertEqual(1, len(line_rules))
        self.assertEqual(51070, line_rule.minscale.value)
        self.assertEqual(102139, line_rule.maxscale.value)
        self.assertEqual(2, line_rule.symbolizers[0].width)

        text_rules = get_text_rule_groups(declarations).get('name', [])
        text_rule = text_rules[0]
        
        self.assertEqual(1, len(text_rules))
        self.assertEqual(51070, text_rule.minscale.value)
        self.assertEqual(102139, text_rule.maxscale.value)
        self.assertEqual(24, text_rule.symbolizers[0].size)

    def testCompile9(self):
        s = u"""
            Layer NAME
            {
                text-face-name: 'Helvetica', 'DejaVu Sans Book';
                text-fill: #f00;
                text-size: 12;
            }
        """
        if MAPNIK_VERSION < 200100:
            # Mapnik only supports multiple font face names as of version 2.1
            return
        
        declarations = stylesheet_declarations(s, is_merc=True)
        text_rule_groups = get_text_rule_groups(declarations)
        
        symbolizer = text_rule_groups['NAME'][0].symbolizers[0]
        fontsets = {symbolizer.get_fontset_name(): output.FontSet(symbolizer.face_name.values).to_mapnik()}
        sym = text_rule_groups['NAME'][0].symbolizers[0].to_mapnik(fontsets)
        
        self.assertEqual(mapnik.Color("#f00"), sym.format.fill if (MAPNIK_VERSION >= 200100) else sym.fill)
        self.assertEqual(12, sym.format.text_size if (MAPNIK_VERSION >= 200100) else sym.text_size)

        # TODO: test for output of FontSet in text symbolizer when Mapnik
        # adds support. See also https://github.com/mapnik/mapnik/issues/1483

    def testCompile10(self):
        """
        """
        s = """<?xml version="1.0"?>
            <Map>
                <Stylesheet>
                    Map { map-bgcolor: #fff; }
                    
                    Layer name
                    {
                        text-face-name: 'Comic Sans', 'Papyrus';
                        text-size: 14;
                        text-fill: #f90;
                    }
                </Stylesheet>
                <Datasource name="template">
                     <Parameter name="type">shape</Parameter>
                     <Parameter name="encoding">latin1</Parameter>
                </Datasource>
                <Layer>
                    <Datasource base="template">
                        <Parameter name="type">shape</Parameter>
                        <Parameter name="file">%(data)s/test.shp</Parameter>
                    </Datasource>
                </Layer>
            </Map>
        """ % self.__dict__

        map = compile(s, self.dirs)
        mmap = mapnik.Map(640, 480)
        
        map.to_mapnik(mmap)
        
        (handle, path) = tempfile.mkstemp(suffix='.xml', prefix='cascadenik-mapnik-')
        os.close(handle)
        
        mapnik.save_map(mmap, path)
        doc = xml.etree.ElementTree.parse(path)
        map_el = doc.getroot()
        
        self.assertEqual(len(map_el.find("Layer").findall('Datasource')), 1)
        params = dict(((p.get('name'), p.text) for p in map_el.find('Layer').find('Datasource').findall('Parameter')))
        self.assertEqual(params['type'], 'shape')
        self.assertTrue(params['file'].endswith('%s/test.shp' % self.data))
        self.assertEqual(params['encoding'], 'latin1')
        
        if MAPNIK_VERSION < 200100:
            # Mapnik only supports multiple font face names as of version 2.1
            textsym_el = map_el.find('Style').find('Rule').find('TextSymbolizer')

            if MAPNIK_VERSION >= 200000:
                # It changed as of 2.0.
                self.assertEqual('Comic Sans', textsym_el.get('face-name'))
            else:
                self.assertEqual('Comic Sans', textsym_el.get('face_name'))

            return
        
        fontset_el = map_el.find('FontSet')

        self.assertEqual('Comic Sans', fontset_el.findall('Font')[0].get('face-name'))
        self.assertEqual('Papyrus', fontset_el.findall('Font')[1].get('face-name'))
        
        if MAPNIK_VERSION >= 200101:
            # Ensure that the fontset-name made it out,
            # see also https://github.com/mapnik/mapnik/issues/1483
            textsym_el = map_el.find('Style').find('Rule').find('TextSymbolizer')
            self.assertEqual(fontset_el.get('name'), textsym_el.get('fontset-name'))

    def testCompile11(self):
        """
        """
        s = """<?xml version="1.0"?>
            <Map>
                <Stylesheet>
                    Map { map-bgcolor: #fff; }
                </Stylesheet>
            </Map>
        """
        map = compile(s, self.dirs, user_styles=['http://cascadenik-sampledata.s3.amazonaws.com/black-bgcolor.css'])
        
        self.assertEqual(str(map.background), '#000000')

class RelativePathTests(unittest.TestCase):

    def setUp(self):
        # directories for all the temp files to be created below
        self.tmpdir1 = os.path.realpath(tempfile.mkdtemp(prefix='cascadenik-tests1-'))
        self.tmpdir2 = os.path.realpath(tempfile.mkdtemp(prefix='cascadenik-tests2-'))

        basepath = os.path.dirname(__file__)
        
        paths = ('paths-test2.mml',
                 'paths-test2.mss',
                 'mission-points/mission-points.dbf',
                 'mission-points/mission-points.prj',
                 'mission-points/mission-points.shp',
                 'mission-points/mission-points.shx',
                 'mission-points.zip',
                 'purple-point.png')

        for path in paths:
            href = urlparse.urljoin('http://cascadenik-sampledata.s3.amazonaws.com', path)
            path = os.path.join(self.tmpdir1, os.path.basename(path))
            file = open(path, 'w')
            file.write(urllib.urlopen(href).read())
            file.close()

    def tearDown(self):
        # destroy the above-created directories
        shutil.rmtree(self.tmpdir1)
        shutil.rmtree(self.tmpdir2)

    def testLocalizedPaths(self):
        
        dirs = Directories(self.tmpdir1, self.tmpdir1, self.tmpdir1)

        mml_path = dirs.output + '/style.mml'
        mml_file = open(mml_path, 'w')
        
        print >> mml_file, """<?xml version="1.0" encoding="utf-8"?>
            <Map srs="+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null">
                <Stylesheet>
                    Layer
                    {
                        point-file: url("http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png");
                    }
                </Stylesheet>
                <Layer srs="+proj=latlong +ellps=WGS84 +datum=WGS84 +no_defs">
                    <Datasource>
                        <Parameter name="type">shape</Parameter>
                        <Parameter name="file">http://cascadenik-sampledata.s3.amazonaws.com/mission-points.zip</Parameter>
                    </Datasource>
                </Layer>
            </Map>
        """
        
        mml_file.close()
        
        map = compile(mml_path, dirs)
        
        img_path = map.layers[0].styles[0].rules[0].symbolizers[0].file
        assert not os.path.isabs(img_path)
        assert os.path.exists(os.path.join(dirs.output, img_path))
        
        shp_path = map.layers[0].datasource.parameters['file'] + '.shp'
        assert not os.path.isabs(shp_path)
        assert os.path.exists(os.path.join(dirs.output, shp_path))

    def testSplitPaths(self):
        
        dirs = Directories(self.tmpdir1, self.tmpdir2, self.tmpdir1)

        mml_path = dirs.output + '/style.mml'
        mml_file = open(mml_path, 'w')
        
        print >> mml_file, """<?xml version="1.0" encoding="utf-8"?>
            <Map srs="+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null">
                <Stylesheet>
                    Layer
                    {
                        point-file: url("http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png");
                    }
                </Stylesheet>
                <Layer srs="+proj=latlong +ellps=WGS84 +datum=WGS84 +no_defs">
                    <Datasource>
                        <Parameter name="type">shape</Parameter>
                        <Parameter name="file">http://cascadenik-sampledata.s3.amazonaws.com/mission-points.zip</Parameter>
                    </Datasource>
                </Layer>
            </Map>
        """
        
        mml_file.close()
        
        map = compile(mml_path, dirs)
        
        img_path = map.layers[0].styles[0].rules[0].symbolizers[0].file
        assert img_path.startswith(dirs.cache)
        assert os.path.exists(img_path)
        
        shp_path = map.layers[0].datasource.parameters['file'] + '.shp'
        assert shp_path.startswith(dirs.cache)
        assert os.path.exists(shp_path)

    def testRelativePaths(self):
    
        dirs = Directories(self.tmpdir1, self.tmpdir1, self.tmpdir1)
        
        mml_path = dirs.output + '/style.mml'
        mml_file = open(mml_path, 'w')
        
        print >> mml_file, """<?xml version="1.0" encoding="utf-8"?>
            <Map srs="+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null">
                <Stylesheet>
                    Layer
                    {
                        point-file: url("purple-point.png");
                    }
                </Stylesheet>
                <Layer srs="+proj=latlong +ellps=WGS84 +datum=WGS84 +no_defs">
                    <Datasource>
                        <Parameter name="type">shape</Parameter>
                        <Parameter name="file">mission-points</Parameter>
                    </Datasource>
                </Layer>
            </Map>
        """
        
        mml_file.close()
        
        map = compile(mml_path, dirs)
        
        img_path = map.layers[0].styles[0].rules[0].symbolizers[0].file
        assert not os.path.isabs(img_path)
        assert os.path.exists(os.path.join(dirs.output, img_path))
        
        shp_path = map.layers[0].datasource.parameters['file'] + '.shp'
        assert not os.path.isabs(shp_path), shp_path
        assert os.path.exists(os.path.join(dirs.output, shp_path))

    def testDistantPaths(self):
    
        dirs = Directories(self.tmpdir2, self.tmpdir2, self.tmpdir1)
        
        mml_path = dirs.output + '/style.mml'
        mml_file = open(mml_path, 'w')
        
        print >> mml_file, """<?xml version="1.0" encoding="utf-8"?>
            <Map srs="+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null">
                <Stylesheet>
                    Layer
                    {
                        point-file: url("purple-point.png");
                    }
                </Stylesheet>
                <Layer srs="+proj=latlong +ellps=WGS84 +datum=WGS84 +no_defs">
                    <Datasource>
                        <Parameter name="type">shape</Parameter>
                        <Parameter name="file">mission-points</Parameter>
                    </Datasource>
                </Layer>
            </Map>
        """
        
        mml_file.close()
        
        map = compile(mml_path, dirs)
        
        img_path = map.layers[0].styles[0].rules[0].symbolizers[0].file
        assert img_path.startswith(dirs.source[7:]), str((img_path, dirs.source[7:]))
        assert os.path.exists(img_path)
        
        shp_path = map.layers[0].datasource.parameters['file'] + '.shp'
        assert shp_path.startswith(dirs.source[7:]), str((shp_path, dirs.source[7:]))
        assert os.path.exists(shp_path)

    def testAbsolutePaths(self):
    
        dirs = Directories(self.tmpdir2, self.tmpdir2, self.tmpdir1)
        
        mml_path = dirs.output + '/style.mml'
        mml_file = open(mml_path, 'w')
        
        print >> mml_file, """<?xml version="1.0" encoding="utf-8"?>
            <Map srs="+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null">
                <Stylesheet>
                    Layer
                    {
                        point-file: url("%s/purple-point.png");
                    }
                </Stylesheet>
                <Layer srs="+proj=latlong +ellps=WGS84 +datum=WGS84 +no_defs">
                    <Datasource>
                        <Parameter name="type">shape</Parameter>
                        <Parameter name="file">%s/mission-points</Parameter>
                    </Datasource>
                </Layer>
            </Map>
        """ % (self.tmpdir1, self.tmpdir1)
        
        mml_file.close()
        
        map = compile(mml_path, dirs)
        
        img_path = map.layers[0].styles[0].rules[0].symbolizers[0].file
        assert img_path.startswith(dirs.source[7:])
        assert os.path.exists(img_path)
        
        shp_path = map.layers[0].datasource.parameters['file'] + '.shp'
        assert shp_path.startswith(dirs.source[7:])
        assert os.path.exists(shp_path)

    def testRemotePaths(self):
        """ MML and MSS files are remote, cache and output to a local directory.
        """
        dirs = Directories(self.tmpdir2, self.tmpdir2, 'http://cascadenik-sampledata.s3.amazonaws.com')
        
        mml_href = 'http://cascadenik-sampledata.s3.amazonaws.com/paths-test.mml'
        
        map = compile(mml_href, dirs)
        
        img_path = map.layers[0].styles[0].rules[0].symbolizers[0].file
        assert not os.path.isabs(img_path)
        assert os.path.exists(os.path.join(dirs.output, img_path))
        
        shp_path = map.layers[0].datasource.parameters['file'] + '.shp'
        assert not os.path.isabs(shp_path)
        assert os.path.exists(os.path.join(dirs.output, shp_path))

    def testRemoteLinkedSheetPaths(self):
        """ MML and MSS files are remote, cache to one local directory and output to a second.
        """
        dirs = Directories(self.tmpdir1, self.tmpdir2, 'http://cascadenik-sampledata.s3.amazonaws.com')
        
        mml_href = 'http://cascadenik-sampledata.s3.amazonaws.com/paths-test2.mml'
        
        map = compile(mml_href, dirs)
        
        img_path = map.layers[0].styles[0].rules[0].symbolizers[0].file
        assert img_path.startswith(dirs.cache), str((img_path, dirs.cache))
        assert os.path.exists(img_path)
        
        shp_path = map.layers[0].datasource.parameters['file'] + '.shp'
        assert shp_path.startswith(dirs.cache), str((shp_path, dirs.cache))
        assert os.path.exists(shp_path)

    def testLocalLinkedSheetPaths(self):
        """ MML and MSS files are in one directory, cache and output to a second.
        """
        dirs = Directories(self.tmpdir2, self.tmpdir2, self.tmpdir1)
        
        mml_path = os.path.join(self.tmpdir1, 'paths-test2.mml')
        
        map = compile(mml_path, dirs)
        
        img_path = map.layers[0].styles[0].rules[0].symbolizers[0].file
        assert img_path.startswith(dirs.source[7:]), str((img_path, dirs.source[7:]))
        assert os.path.exists(img_path)
        
        shp_path = map.layers[0].datasource.parameters['file'] + '.shp'
        assert not os.path.isabs(shp_path)
        assert os.path.exists(os.path.join(dirs.output, shp_path))

    def testSplitLinkedSheetPaths(self):
        """ MML and MSS files are in one directory, cache in that same directory, and output to a second.
        """
        dirs = Directories(self.tmpdir2, self.tmpdir1, self.tmpdir1)
        
        mml_path = os.path.join(self.tmpdir1, 'paths-test2.mml')
        
        map = compile(mml_path, dirs)
        
        img_path = map.layers[0].styles[0].rules[0].symbolizers[0].file
        assert img_path.startswith(dirs.source[7:]), str((img_path, dirs.source[7:]))
        assert os.path.exists(img_path)
        
        shp_path = map.layers[0].datasource.parameters['file'] + '.shp'
        assert shp_path.startswith(dirs.cache), str((shp_path, dirs.cache))
        assert os.path.exists(shp_path)

    def testReflexivePaths(self):
        """ MML file is at a remote location, but it references a local resource by file://.
        """
        dirs = Directories(self.tmpdir2, self.tmpdir2, 'http://cascadenik-sampledata.s3.amazonaws.com')
        
        mml_data = """<?xml version="1.0" encoding="utf-8"?>
            <Map srs="+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null">
                <Stylesheet>
                    Layer
                    {
                        point-file: url("file://%s/purple-point.png");
                    }
                </Stylesheet>
                <Layer srs="+proj=latlong +ellps=WGS84 +datum=WGS84 +no_defs">
                    <Datasource>
                        <Parameter name="type">shape</Parameter>
                        <Parameter name="file">file://%s/mission-points</Parameter>
                    </Datasource>
                </Layer>
            </Map>
        """ % (self.tmpdir1, self.tmpdir1)
        
        map = compile(mml_data, dirs)
        
        img_path = map.layers[0].styles[0].rules[0].symbolizers[0].file
        assert img_path.startswith(self.tmpdir1), 'Assert that "%s" starts with "%s"' % (img_path, self.tmpdir1)
        assert os.path.exists(img_path)
        
        shp_path = map.layers[0].datasource.parameters['file'] + '.shp'
        assert shp_path.startswith(self.tmpdir1), 'Assert that "%s" starts with "%s"' % (shp_path, self.tmpdir1)
        assert os.path.exists(shp_path)
    
    def testDotDotStylePaths(self):
        """ MML file is in a subdirectory, MSS is outside that subdirectory with relative resources.
        """
        dirs = Directories(self.tmpdir2, self.tmpdir2, self.tmpdir1 + '/sub')
        
        mml_data = """<?xml version="1.0" encoding="utf-8"?>
            <Map srs="+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null">
                <Stylesheet src="../paths-test2.mss"/>
                <Layer srs="+proj=latlong +ellps=WGS84 +datum=WGS84 +no_defs">
                    <Datasource>
                        <Parameter name="type">shape</Parameter>
                        <Parameter name="file">file://%s/mission-points</Parameter>
                    </Datasource>
                </Layer>
            </Map>
        """ % self.tmpdir1
        
        map = compile(mml_data, dirs)
        
        img_path = map.layers[0].styles[0].rules[0].symbolizers[0].file
        assert img_path.startswith(self.tmpdir1), 'Assert that "%s" starts with "%s"' % (img_path, self.tmpdir1)
        assert os.path.exists(img_path)
        
        shp_path = map.layers[0].datasource.parameters['file'] + '.shp'
        assert shp_path.startswith(self.tmpdir1), 'Assert that "%s" starts with "%s"' % (shp_path, self.tmpdir1)
        assert os.path.exists(shp_path)
    
    def testSubdirStylePaths(self):
        """ MML file is in a directory, MSS is in a subdirectory with relative resources.
        """
        dirs = Directories(self.tmpdir2, self.tmpdir2, self.tmpdir1 + '/..')
        
        mml_data = """<?xml version="1.0" encoding="utf-8"?>
            <Map srs="+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null">
                <Stylesheet src="%s/paths-test2.mss"/>
                <Layer srs="+proj=latlong +ellps=WGS84 +datum=WGS84 +no_defs">
                    <Datasource>
                        <Parameter name="type">shape</Parameter>
                        <Parameter name="file">file://%s/mission-points</Parameter>
                    </Datasource>
                </Layer>
            </Map>
        """ % (os.path.basename(self.tmpdir1), self.tmpdir1)
        
        map = compile(mml_data, dirs)
        
        img_path = map.layers[0].styles[0].rules[0].symbolizers[0].file
        assert img_path.startswith(self.tmpdir1), 'Assert that "%s" starts with "%s"' % (img_path, self.tmpdir1)
        assert os.path.exists(img_path)
        
        shp_path = map.layers[0].datasource.parameters['file'] + '.shp'
        assert shp_path.startswith(self.tmpdir1), 'Assert that "%s" starts with "%s"' % (shp_path, self.tmpdir1)
        assert os.path.exists(shp_path)
        
if __name__ == '__main__':
    unittest.main()
    
