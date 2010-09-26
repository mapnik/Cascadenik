# -*- coding: utf-8 -*-

import os
import sys
import shutil
import unittest
import tempfile
import xml.etree.ElementTree

try:
    import mapnik2 as mapnik
except ImportError:
    import mapnik

from cascadenik.style import ParseException, stylesheet_rulesets, rulesets_declarations, stylesheet_declarations
from cascadenik.style import Selector, SelectorElement, SelectorAttributeTest
from cascadenik.style import postprocess_property, postprocess_value, Property
from cascadenik.style import color, numbers, boolean
from cascadenik.compile import tests_filter_combinations, Filter, selectors_tests
from cascadenik.compile import filtered_property_declarations, is_applicable_selector
from cascadenik.compile import get_polygon_rules, get_line_rules, get_text_rule_groups, get_shield_rule_groups
from cascadenik.compile import get_point_rules, get_polygon_pattern_rules, get_line_pattern_rules
from cascadenik.compile import test2str, compile
from cascadenik.compile import auto_detect_mapnik_version
from cascadenik.sources import DataSources
import cascadenik.output as output
    
MAPNIK_AUTO_IMAGE_SUPPORT = False
ver = auto_detect_mapnik_version()
if ver:
    MAPNIK_AUTO_IMAGE_SUPPORT = (ver >= 701)

class ParseTests(unittest.TestCase):
    
    def testBadSelector1(self):
        self.assertRaises(ParseException, stylesheet_rulesets, 'Too Many Things { }')

    def testBadSelector2(self):
        self.assertRaises(ParseException, stylesheet_rulesets, '{ }')

    def testBadSelector3(self):
        self.assertRaises(ParseException, stylesheet_rulesets, 'Illegal { }')

    def testBadSelector4(self):
        self.assertRaises(ParseException, stylesheet_rulesets, 'Layer foo[this=that] { }')

    def testBadSelector5(self):
        self.assertRaises(ParseException, stylesheet_rulesets, 'Layer[this>that] foo { }')

    def testBadSelector6(self):
        self.assertRaises(ParseException, stylesheet_rulesets, 'Layer foo#bar { }')

    def testBadSelector7(self):
        self.assertRaises(ParseException, stylesheet_rulesets, 'Layer foo.bar { }')

    def testBadSelectorTest1(self):
        self.assertRaises(ParseException, stylesheet_rulesets, 'Layer[foo>] { }')

    def testBadSelectorTest2(self):
        self.assertRaises(ParseException, stylesheet_rulesets, 'Layer[foo><bar] { }')

    def testBadSelectorTest3(self):
        self.assertRaises(ParseException, stylesheet_rulesets, 'Layer[foo<<bar] { }')

    def testBadSelectorTest4(self):
        self.assertRaises(ParseException, stylesheet_rulesets, 'Layer[<bar] { }')

    def testBadSelectorTest5(self):
        self.assertRaises(ParseException, stylesheet_rulesets, 'Layer[<<bar] { }')

    def testBadProperty1(self):
        self.assertRaises(ParseException, stylesheet_rulesets, 'Layer { unknown-property: none; }')

    def testBadProperty2(self):
        self.assertRaises(ParseException, stylesheet_rulesets, 'Layer { extra thing: none; }')

    def testBadProperty3(self):
        self.assertRaises(ParseException, stylesheet_rulesets, 'Layer { "not an ident": none; }')

    def testRulesets1(self):
        self.assertEqual(0, len(stylesheet_rulesets('/* empty stylesheet */')))

    def testRulesets2(self):
        self.assertEqual(1, len(stylesheet_rulesets('Layer { }')))

    def testRulesets3(self):
        self.assertEqual(2, len(stylesheet_rulesets('Layer { } Layer { }')))

    def testRulesets4(self):
        self.assertEqual(3, len(stylesheet_rulesets('Layer { } /* something */ Layer { } /* extra */ Layer { }')))

    def testRulesets5(self):
        self.assertEqual(1, len(stylesheet_rulesets('Map { }')))

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

class PropertyTests(unittest.TestCase):

    def testProperty1(self):
        self.assertRaises(ParseException, postprocess_property, [('IDENT', 'too-many'), ('IDENT', 'properties')])

    def testProperty2(self):
        self.assertRaises(ParseException, postprocess_property, [])

    def testProperty3(self):
        self.assertRaises(ParseException, postprocess_property, [('IDENT', 'illegal-property')])

    def testProperty4(self):
        self.assertEqual('shield', postprocess_property([('IDENT', 'shield-fill')]).group())

    def testProperty5(self):
        self.assertEqual('shield', postprocess_property([('S', ' '), ('IDENT', 'shield-fill'), ('COMMENT', 'ignored comment')]).group())

class ValueTests(unittest.TestCase):

    def testBadValue1(self):
        self.assertRaises(ParseException, postprocess_value, [], Property('polygon-opacity'))

    def testBadValue2(self):
        self.assertRaises(ParseException, postprocess_value, [('IDENT', 'too'), ('IDENT', 'many')], Property('polygon-opacity'))

    def testBadValue3(self):
        self.assertRaises(ParseException, postprocess_value, [('IDENT', 'non-number')], Property('polygon-opacity'))

    def testBadValue3b(self):
        self.assertRaises(ParseException, postprocess_value, [('IDENT', 'non-number')], Property('polygon-gamma'))

    def testBadValue4(self):
        self.assertRaises(ParseException, postprocess_value, [('IDENT', 'non-string')], Property('text-face-name'))

    def testBadValue5(self):
        self.assertRaises(ParseException, postprocess_value, [('IDENT', 'non-hash')], Property('polygon-fill'))

    def testBadValue6(self):
        self.assertRaises(ParseException, postprocess_value, [('HASH', '#badcolor')], Property('polygon-fill'))

    def testBadValue7(self):
        self.assertRaises(ParseException, postprocess_value, [('IDENT', 'non-URI')], Property('point-file'))

    def testBadValue8(self):
        self.assertRaises(ParseException, postprocess_value, [('IDENT', 'bad-boolean')], Property('text-avoid-edges'))

    def testBadValue9(self):
        self.assertRaises(ParseException, postprocess_value, [('STRING', 'not an IDENT')], Property('line-join'))

    def testBadValue10(self):
        self.assertRaises(ParseException, postprocess_value, [('IDENT', 'not-in-tuple')], Property('line-join'))

    def testBadValue11(self):
        self.assertRaises(ParseException, postprocess_value, [('NUMBER', '1'), ('CHAR', ','), ('CHAR', ','), ('NUMBER', '3')], Property('line-dasharray'))

    def testValue1(self):
        self.assertEqual(1.0, postprocess_value([('NUMBER', '1.0')], Property('polygon-opacity')).value)

    def testValue1b(self):
        self.assertEqual(1.0, postprocess_value([('NUMBER', '1.0')], Property('polygon-gamma')).value)

    def testValue2(self):
        self.assertEqual(10, postprocess_value([('NUMBER', '10')], Property('line-width')).value)

    def testValue2b(self):
        self.assertEqual(-10, postprocess_value([('CHAR', '-'), ('NUMBER', '10')], Property('text-dx')).value)

    def testValue3(self):
        self.assertEqual('DejaVu', str(postprocess_value([('STRING', '"DejaVu"')], Property('text-face-name'))))

    def testValue4(self):
        self.assertEqual('#ff9900', str(postprocess_value([('HASH', '#ff9900')], Property('map-bgcolor'))))

    def testValue5(self):
        self.assertEqual('#ff9900', str(postprocess_value([('HASH', '#f90')], Property('map-bgcolor'))))

    def testValue6(self):
        self.assertEqual('http://example.com', str(postprocess_value([('URI', 'url("http://example.com")')], Property('point-file'))))

    def testValue7(self):
        self.assertEqual('true', str(postprocess_value([('IDENT', 'true')], Property('text-avoid-edges'))))

    def testValue8(self):
        self.assertEqual('false', str(postprocess_value([('IDENT', 'false')], Property('text-avoid-edges'))))

    def testValue9(self):
        self.assertEqual('bevel', str(postprocess_value([('IDENT', 'bevel')], Property('line-join'))))

    def testValue10(self):
        self.assertEqual('1,2,3', str(postprocess_value([('NUMBER', '1'), ('CHAR', ','), ('NUMBER', '2'), ('CHAR', ','), ('NUMBER', '3')], Property('line-dasharray'))))

    def testValue11(self):
        self.assertEqual('1,2.0,3', str(postprocess_value([('NUMBER', '1'), ('CHAR', ','), ('S', ' '), ('NUMBER', '2.0'), ('CHAR', ','), ('NUMBER', '3')], Property('line-dasharray'))))

    def testValue12(self):
        self.assertEqual(12, postprocess_value([('NUMBER', '12')], Property('text-character-spacing')).value)

    def testValue13(self):
        self.assertEqual(14, postprocess_value([('NUMBER', '14')], Property('shield-character-spacing')).value)

    def testValue14(self):
        self.assertEqual(12, postprocess_value([('NUMBER', '12')], Property('text-line-spacing')).value)

    def testValue15(self):
        self.assertEqual(14, postprocess_value([('NUMBER', '14')], Property('shield-line-spacing')).value)
    
class CascadeTests(unittest.TestCase):

    def testCascade1(self):
        s = """
            Layer
            {
                text-dx: -10;
                text-dy: -10;
            }
        """
        rulesets = stylesheet_rulesets(s)
        
        self.assertEqual(1, len(rulesets))
        self.assertEqual(1, len(rulesets[0]['selectors']))
        self.assertEqual(1, len(rulesets[0]['selectors'][0].elements))

        self.assertEqual(2, len(rulesets[0]['declarations']))
        self.assertEqual('text-dx', rulesets[0]['declarations'][0]['property'].name)
        self.assertEqual(-10, rulesets[0]['declarations'][0]['value'].value)
        
        declarations = rulesets_declarations(rulesets)
        
        self.assertEqual(2, len(declarations))
        self.assertEqual('text-dx', declarations[0].property.name)
        self.assertEqual('text-dy', declarations[1].property.name)

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
        rulesets = stylesheet_rulesets(s)
        
        self.assertEqual(2, len(rulesets))
        self.assertEqual(1, len(rulesets[0]['selectors']))
        self.assertEqual(1, len(rulesets[0]['selectors'][0].elements))
        self.assertEqual(2, len(rulesets[1]['selectors']))
        self.assertEqual(2, len(rulesets[1]['selectors'][0].elements))
        self.assertEqual(1, len(rulesets[1]['selectors'][1].elements))
        
        declarations = rulesets_declarations(rulesets)

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
        rulesets = stylesheet_rulesets(s)
        selectors = [dec.selector for dec in rulesets_declarations(rulesets)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual("[landuse] = 'military'", test2str(filters[1].tests[0]))

    def testFilters2(self):
        s = """
            Layer[landuse='military'] { polygon-fill: #000; }
        """
        rulesets = stylesheet_rulesets(s)
        selectors = [dec.selector for dec in rulesets_declarations(rulesets)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual("[landuse] = 'military'", test2str(filters[1].tests[0]))

    def testFilters3(self):
        s = """
            Layer[landuse="military"] { polygon-fill: #000; }
        """
        rulesets = stylesheet_rulesets(s)
        selectors = [dec.selector for dec in rulesets_declarations(rulesets)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual("[landuse] = 'military'", test2str(filters[1].tests[0]))

    def testFilters4(self):
        s = """
            Layer[foo=1] { polygon-fill: #000; }
        """
        rulesets = stylesheet_rulesets(s)
        selectors = [dec.selector for dec in rulesets_declarations(rulesets)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual("[foo] = 1", test2str(filters[1].tests[0]))

    def testFilters5(self):
        s = """
            Layer[foo=1.1] { polygon-fill: #000; }
        """
        rulesets = stylesheet_rulesets(s)
        selectors = [dec.selector for dec in rulesets_declarations(rulesets)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual("[foo] = 1.1", test2str(filters[1].tests[0]))

    def testFilters6(self):
        s = """
            Layer[foo="1.1"] { polygon-fill: #000; }
        """
        rulesets = stylesheet_rulesets(s)
        selectors = [dec.selector for dec in rulesets_declarations(rulesets)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual("[foo] = '1.1'", test2str(filters[1].tests[0]))

    def testFilters7(self):
        s = """
            Layer[landuse= "military"] { polygon-fill: #000; }
        """
        rulesets = stylesheet_rulesets(s)
        selectors = [dec.selector for dec in rulesets_declarations(rulesets)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual("[landuse] = 'military'", test2str(filters[1].tests[0]))

    def testFilters8(self):
        s = """
            Layer[foo =1] { polygon-fill: #000; }
        """
        rulesets = stylesheet_rulesets(s)
        selectors = [dec.selector for dec in rulesets_declarations(rulesets)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual("[foo] = 1", test2str(filters[1].tests[0]))

    def testFilters9(self):
        s = """
            Layer[foo = "1.1"] { polygon-fill: #000; }
        """
        rulesets = stylesheet_rulesets(s)
        selectors = [dec.selector for dec in rulesets_declarations(rulesets)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual("[foo] = '1.1'", test2str(filters[1].tests[0]))

    def testFilters10(self):
        # Unicode is fine in filter values
        # Not so much in properties
        s = u'''
        Layer[name="Grüner Strich"] { polygon-fill: #000; }
        '''
        rulesets = stylesheet_rulesets(s)
        selectors = [dec.selector for dec in rulesets_declarations(rulesets)]
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
        declarations = stylesheet_declarations(s, is_gym=True)
        text_rule_groups = get_text_rule_groups(declarations)
        
        self.assertEqual(str, type(text_rule_groups.keys()[0]))
        self.assertEqual(str, type(text_rule_groups['CODE'][0].symbolizers[0].face_name))
        self.assertEqual(str, type(text_rule_groups['CODE'][0].symbolizers[0].placement))

class FilterCombinationTests(unittest.TestCase):

    def testFilters1(self):
        s = """
            Layer[landuse=military]     { polygon-fill: #000; }
            Layer[landuse=civilian]     { polygon-fill: #001; }
            Layer[landuse=agriculture]  { polygon-fill: #010; }
        """
        rulesets = stylesheet_rulesets(s)
        selectors = [dec.selector for dec in rulesets_declarations(rulesets)]
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
        rulesets = stylesheet_rulesets(s)
        selectors = [dec.selector for dec in rulesets_declarations(rulesets)]
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
        rulesets = stylesheet_rulesets(s)
        selectors = [dec.selector for dec in rulesets_declarations(rulesets)]
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
        rulesets = stylesheet_rulesets(s)
        selectors = [dec.selector for dec in rulesets_declarations(rulesets)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual(len(filters), 16)
        self.assertEqual(str(sorted(filters)), '[[horse!=yes][landuse!=agriculture][landuse!=civilian][landuse!=military][leisure!=park], [horse!=yes][landuse!=agriculture][landuse!=civilian][landuse!=military][leisure=park], [horse!=yes][landuse=agriculture][leisure!=park], [horse!=yes][landuse=agriculture][leisure=park], [horse!=yes][landuse=civilian][leisure!=park], [horse!=yes][landuse=civilian][leisure=park], [horse!=yes][landuse=military][leisure!=park], [horse!=yes][landuse=military][leisure=park], [horse=yes][landuse!=agriculture][landuse!=civilian][landuse!=military][leisure!=park], [horse=yes][landuse!=agriculture][landuse!=civilian][landuse!=military][leisure=park], [horse=yes][landuse=agriculture][leisure!=park], [horse=yes][landuse=agriculture][leisure=park], [horse=yes][landuse=civilian][leisure!=park], [horse=yes][landuse=civilian][leisure=park], [horse=yes][landuse=military][leisure!=park], [horse=yes][landuse=military][leisure=park]]')

class SimpleRangeTests(unittest.TestCase):

    def testRanges1(self):
        s = """
            Layer[foo<1000] { polygon-fill: #000; }
            Layer[foo>1000] { polygon-fill: #001; }
        """
        rulesets = stylesheet_rulesets(s)
        selectors = [dec.selector for dec in rulesets_declarations(rulesets)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual(len(filters), 3)
        self.assertEqual(str(sorted(filters)), '[[foo<1000], [foo=1000], [foo>1000]]')

    def testRanges2(self):
        s = """
            Layer[foo>1] { polygon-fill: #000; }
            Layer[foo<2] { polygon-fill: #001; }
        """
        rulesets = stylesheet_rulesets(s)
        selectors = [dec.selector for dec in rulesets_declarations(rulesets)]
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
        rulesets = stylesheet_rulesets(s)
        selectors = [dec.selector for dec in rulesets_declarations(rulesets)]
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
        rulesets = stylesheet_rulesets(s)
        selectors = [dec.selector for dec in rulesets_declarations(rulesets)]
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
        rulesets = stylesheet_rulesets(s)
        selectors = [dec.selector for dec in rulesets_declarations(rulesets)]
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

        declarations = stylesheet_declarations(s, is_gym=True)
        rules = get_polygon_rules(declarations, target_dir=self.tmpdir)
        
        self.assertEqual(399999, rules[0].maxscale.value)
        self.assertEqual(color(0xCC, 0xCC, 0xCC), rules[0].symbolizers[0].color)
        self.assertEqual("[use] = 'cemetery'", rules[0].filter.text)
        
        self.assertEqual(399999, rules[1].maxscale.value)
        self.assertEqual(color(0x66, 0xFF, 0x66), rules[1].symbolizers[0].color)
        self.assertEqual("[use] = 'park'", rules[1].filter.text)
    
        self.assertEqual(400000, rules[2].minscale.value)
        self.assertEqual(color(0x99, 0x99, 0x99), rules[2].symbolizers[0].color)
        self.assertEqual("[use] = 'cemetery'", rules[2].filter.text)
        
        self.assertEqual(400000, rules[3].minscale.value)
        self.assertEqual(color(0x00, 0xFF, 0x00), rules[3].symbolizers[0].color)
        self.assertEqual("[use] = 'park'", rules[3].filter.text)

    def testStyleRules02(self):
        s = """
            Layer[zoom<=10][foo<1] { polygon-fill: #000; }
            Layer[zoom<=10][foo>1] { polygon-fill: #00f; }
            Layer[zoom>10][foo<1] { polygon-fill: #0f0; }
            Layer[zoom>10][foo>1] { polygon-fill: #f00; }
        """
    
        declarations = stylesheet_declarations(s, is_gym=True)
        rules = get_polygon_rules(declarations, target_dir=self.tmpdir)
        
        self.assertEqual(399999, rules[0].maxscale.value)
        self.assertEqual(color(0x00, 0xFF, 0x00), rules[0].symbolizers[0].color)
        self.assertEqual('[foo] < 1', rules[0].filter.text)
        
        self.assertEqual(399999, rules[1].maxscale.value)
        self.assertEqual(color(0xFF, 0x00, 0x00), rules[1].symbolizers[0].color)
        self.assertEqual('[foo] > 1', rules[1].filter.text)
    
        self.assertEqual(400000, rules[2].minscale.value)
        self.assertEqual(color(0x00, 0x00, 0x00), rules[2].symbolizers[0].color)
        self.assertEqual('[foo] < 1', rules[2].filter.text)
        
        self.assertEqual(400000, rules[3].minscale.value)
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
    
        declarations = stylesheet_declarations(s, is_gym=True)

        poly_rules = get_polygon_rules(declarations, target_dir=self.tmpdir)
        
        self.assertEqual(399999, poly_rules[0].maxscale.value)
        self.assertEqual(color(0x00, 0xFF, 0x00), poly_rules[0].symbolizers[0].color)
        self.assertEqual('[foo] < 1', poly_rules[0].filter.text)
        
        self.assertEqual(399999, poly_rules[1].maxscale.value)
        self.assertEqual(color(0xFF, 0x00, 0x00), poly_rules[1].symbolizers[0].color)
        self.assertEqual('[foo] > 1', poly_rules[1].filter.text)
    
        self.assertEqual(400000, poly_rules[2].minscale.value)
        self.assertEqual(color(0x00, 0x00, 0x00), poly_rules[2].symbolizers[0].color)
        self.assertEqual('[foo] < 1', poly_rules[2].filter.text)
        
        self.assertEqual(400000, poly_rules[3].minscale.value)
        self.assertEqual(color(0x00, 0x00, 0xFF), poly_rules[3].symbolizers[0].color)
        self.assertEqual('[foo] > 1', poly_rules[3].filter.text)
        
        line_rules = get_line_rules(declarations, target_dir=self.tmpdir)

        self.assertEqual(399999, line_rules[0].maxscale.value)
        self.assertEqual(color(0x00, 0xFF, 0xFF), line_rules[0].symbolizers[0].color)
        self.assertEqual(2.0, line_rules[0].symbolizers[0].width)
        self.assertEqual('[foo] < 1', line_rules[0].filter.text)
        
        self.assertEqual(399999, line_rules[1].maxscale.value)
        self.assertEqual(color(0xFF, 0x00, 0xFF), line_rules[1].symbolizers[0].color)
        self.assertEqual(2.0, line_rules[1].symbolizers[0].width)
        self.assertEqual('[foo] = 1', line_rules[1].filter.text)
    
        self.assertEqual(399999, line_rules[2].maxscale.value)
        self.assertEqual(color(0xFF, 0xFF, 0x00), line_rules[2].symbolizers[0].color)
        self.assertEqual(2.0, line_rules[2].symbolizers[0].width)
        self.assertEqual('[foo] > 1', line_rules[2].filter.text)
    
        self.assertEqual(400000, line_rules[3].minscale.value)
        self.assertEqual(color(0x00, 0xFF, 0xFF), line_rules[3].symbolizers[0].color)
        self.assertEqual(1.0, line_rules[3].symbolizers[0].width)
        self.assertEqual('[foo] < 1', line_rules[3].filter.text)
        
        self.assertEqual(400000, line_rules[4].minscale.value)
        self.assertEqual(color(0xFF, 0x00, 0xFF), line_rules[4].symbolizers[0].color)
        self.assertEqual(1.0, line_rules[4].symbolizers[0].width)
        self.assertEqual('[foo] = 1', line_rules[4].filter.text)
        
        self.assertEqual(400000, line_rules[5].minscale.value)
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
    
        declarations = stylesheet_declarations(s, is_gym=True)
        
        line_rules = get_line_rules(declarations, target_dir=self.tmpdir)

        self.assertEqual(399999, line_rules[0].maxscale.value)
        self.assertEqual(color(0x00, 0xFF, 0xFF), line_rules[0].symbolizers[0].color)
        self.assertEqual(2.0, line_rules[0].symbolizers[0].width)
        self.assertEqual('[foo] < 1', line_rules[0].filter.text)
        
        self.assertEqual(399999, line_rules[1].maxscale.value)
        self.assertEqual(color(0xFF, 0x00, 0xFF), line_rules[1].symbolizers[0].color)
        self.assertEqual(2.0, line_rules[1].symbolizers[0].width)
        self.assertEqual('[foo] = 1', line_rules[1].filter.text)
    
        self.assertEqual(399999, line_rules[2].maxscale.value)
        self.assertEqual(color(0xFF, 0xFF, 0x00), line_rules[2].symbolizers[0].color)
        self.assertEqual(2.0, line_rules[2].symbolizers[0].width)
        self.assertEqual('[foo] > 1', line_rules[2].filter.text)
    
        self.assertEqual(400000, line_rules[3].minscale.value)
        self.assertEqual(color(0x00, 0xFF, 0xFF), line_rules[3].symbolizers[0].color)
        self.assertEqual(1.0, line_rules[3].symbolizers[0].width)
        self.assertEqual('[foo] < 1', line_rules[3].filter.text)
        
        self.assertEqual(400000, line_rules[4].minscale.value)
        self.assertEqual(color(0xFF, 0x00, 0xFF), line_rules[4].symbolizers[0].color)
        self.assertEqual(1.0, line_rules[4].symbolizers[0].width)
        self.assertEqual('[foo] = 1', line_rules[4].filter.text)
        
        self.assertEqual(400000, line_rules[5].minscale.value)
        self.assertEqual(color(0xFF, 0xFF, 0x00), line_rules[5].symbolizers[0].color)
        self.assertEqual(1.0, line_rules[5].symbolizers[0].width)
        self.assertEqual('[foo] > 1', line_rules[5].filter.text)
        
        text_rule_groups = get_text_rule_groups(declarations)
        
        self.assertEqual(399999, text_rule_groups['label'][0].maxscale.value)
        self.assertEqual('Arial', text_rule_groups['label'][0].symbolizers[0].face_name)
        self.assertEqual(12, text_rule_groups['label'][0].symbolizers[0].size)
        self.assertEqual('[foo] < 1', text_rule_groups['label'][0].filter.text)
        
        self.assertEqual(399999, text_rule_groups['label'][1].maxscale.value)
        self.assertEqual('Helvetica', text_rule_groups['label'][1].symbolizers[0].face_name)
        self.assertEqual(12, text_rule_groups['label'][1].symbolizers[0].size)
        self.assertEqual('[foo] >= 1', text_rule_groups['label'][1].filter.text)
    
        self.assertEqual(400000, text_rule_groups['label'][2].minscale.value)
        self.assertEqual('Arial', text_rule_groups['label'][2].symbolizers[0].face_name)
        self.assertEqual(10, text_rule_groups['label'][2].symbolizers[0].size)
        self.assertEqual('[foo] < 1', text_rule_groups['label'][2].filter.text)
        
        self.assertEqual(400000, text_rule_groups['label'][3].minscale.value)
        self.assertEqual('Helvetica', text_rule_groups['label'][3].symbolizers[0].face_name)
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
    
        declarations = stylesheet_declarations(s, is_gym=True)
        
        text_rule_groups = get_text_rule_groups(declarations)
        
        self.assertEqual(399999, text_rule_groups['label'][0].maxscale.value)
        self.assertEqual('Arial', text_rule_groups['label'][0].symbolizers[0].face_name)
        self.assertEqual(12, text_rule_groups['label'][0].symbolizers[0].size)
        self.assertEqual('[foo] < 1', text_rule_groups['label'][0].filter.text)
        
        self.assertEqual(399999, text_rule_groups['label'][1].maxscale.value)
        self.assertEqual('Helvetica', text_rule_groups['label'][1].symbolizers[0].face_name)
        self.assertEqual(12, text_rule_groups['label'][1].symbolizers[0].size)
        self.assertEqual('[foo] >= 1', text_rule_groups['label'][1].filter.text)
    
        self.assertEqual(400000, text_rule_groups['label'][2].minscale.value)
        self.assertEqual('Arial', text_rule_groups['label'][2].symbolizers[0].face_name)
        self.assertEqual(10, text_rule_groups['label'][2].symbolizers[0].size)
        self.assertEqual('[foo] < 1', text_rule_groups['label'][2].filter.text)
        
        self.assertEqual(400000, text_rule_groups['label'][3].minscale.value)
        self.assertEqual('Helvetica', text_rule_groups['label'][3].symbolizers[0].face_name)
        self.assertEqual(10, text_rule_groups['label'][3].symbolizers[0].size)
        self.assertEqual('[foo] >= 1', text_rule_groups['label'][3].filter.text)
        
        shield_rule_groups = get_shield_rule_groups(declarations, target_dir=self.tmpdir)
        
        assert shield_rule_groups['label'][0].minscale is None
        assert shield_rule_groups['label'][0].maxscale is None
        self.assertEqual('Helvetica', shield_rule_groups['label'][0].symbolizers[0].face_name)
        self.assertEqual(12, shield_rule_groups['label'][0].symbolizers[0].size)
        if not MAPNIK_AUTO_IMAGE_SUPPORT:
            self.assertEqual(8, shield_rule_groups['label'][0].symbolizers[0].width)
            self.assertEqual(8, shield_rule_groups['label'][0].symbolizers[0].height)
        self.assertEqual("not [bar] = 'baz' and not [bar] = 'quux' and [foo] <= 1", shield_rule_groups['label'][0].filter.text)
        
        assert shield_rule_groups['label'][1].minscale is None
        assert shield_rule_groups['label'][1].maxscale is None
        self.assertEqual('Helvetica', shield_rule_groups['label'][1].symbolizers[0].face_name)
        self.assertEqual(10, shield_rule_groups['label'][1].symbolizers[0].size)
        if not MAPNIK_AUTO_IMAGE_SUPPORT:
            self.assertEqual(8, shield_rule_groups['label'][1].symbolizers[0].width)
            self.assertEqual(8, shield_rule_groups['label'][1].symbolizers[0].height)
        self.assertEqual("not [bar] = 'baz' and not [bar] = 'quux' and [foo] > 1", shield_rule_groups['label'][1].filter.text)
        
        assert shield_rule_groups['label'][2].minscale is None
        assert shield_rule_groups['label'][2].maxscale is None
        self.assertEqual('Helvetica', shield_rule_groups['label'][2].symbolizers[0].face_name)
        self.assertEqual(14, shield_rule_groups['label'][2].symbolizers[0].size)
        if not MAPNIK_AUTO_IMAGE_SUPPORT:
            self.assertEqual(8, shield_rule_groups['label'][2].symbolizers[0].width)
            self.assertEqual(8, shield_rule_groups['label'][2].symbolizers[0].height)
        self.assertEqual("[bar] = 'baz' and [foo] <= 1", shield_rule_groups['label'][2].filter.text)
        
        assert shield_rule_groups['label'][3].minscale is None
        assert shield_rule_groups['label'][3].maxscale is None
        self.assertEqual('Helvetica', shield_rule_groups['label'][3].symbolizers[0].face_name)
        self.assertEqual(14, shield_rule_groups['label'][3].symbolizers[0].size)
        if not MAPNIK_AUTO_IMAGE_SUPPORT:
            self.assertEqual(8, shield_rule_groups['label'][3].symbolizers[0].width)
            self.assertEqual(8, shield_rule_groups['label'][3].symbolizers[0].height)
        self.assertEqual("[bar] = 'baz' and [foo] > 1", shield_rule_groups['label'][3].filter.text)
        
        assert shield_rule_groups['label'][4].minscale is None
        assert shield_rule_groups['label'][4].maxscale is None
        self.assertEqual('Helvetica', shield_rule_groups['label'][4].symbolizers[0].face_name)
        self.assertEqual(16, shield_rule_groups['label'][4].symbolizers[0].size)
        if not MAPNIK_AUTO_IMAGE_SUPPORT:
            self.assertEqual(8, shield_rule_groups['label'][4].symbolizers[0].width)
            self.assertEqual(8, shield_rule_groups['label'][4].symbolizers[0].height)
        self.assertEqual("[bar] = 'quux' and [foo] <= 1", shield_rule_groups['label'][4].filter.text)
        
        assert shield_rule_groups['label'][5].minscale is None
        assert shield_rule_groups['label'][5].maxscale is None
        self.assertEqual('Helvetica', shield_rule_groups['label'][5].symbolizers[0].face_name)
        self.assertEqual(16, shield_rule_groups['label'][5].symbolizers[0].size)
        if not MAPNIK_AUTO_IMAGE_SUPPORT:
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
    
        declarations = stylesheet_declarations(s, is_gym=True)
        
        shield_rule_groups = get_shield_rule_groups(declarations, target_dir=self.tmpdir)
        
        assert shield_rule_groups['label'][0].minscale is None
        assert shield_rule_groups['label'][0].maxscale is None
        self.assertEqual('Helvetica', shield_rule_groups['label'][0].symbolizers[0].face_name)
        self.assertEqual(12, shield_rule_groups['label'][0].symbolizers[0].size)
        if not MAPNIK_AUTO_IMAGE_SUPPORT:
            self.assertEqual(8, shield_rule_groups['label'][0].symbolizers[0].width)
            self.assertEqual(8, shield_rule_groups['label'][0].symbolizers[0].height)
        self.assertEqual("not [bar] = 'baz' and not [bar] = 'quux' and [foo] <= 1", shield_rule_groups['label'][0].filter.text)
        
        assert shield_rule_groups['label'][1].minscale is None
        assert shield_rule_groups['label'][1].maxscale is None
        self.assertEqual('Helvetica', shield_rule_groups['label'][1].symbolizers[0].face_name)
        self.assertEqual(10, shield_rule_groups['label'][1].symbolizers[0].size)
        if not MAPNIK_AUTO_IMAGE_SUPPORT:
            self.assertEqual(8, shield_rule_groups['label'][1].symbolizers[0].width)
            self.assertEqual(8, shield_rule_groups['label'][1].symbolizers[0].height)
        self.assertEqual("not [bar] = 'baz' and not [bar] = 'quux' and [foo] > 1", shield_rule_groups['label'][1].filter.text)
        
        assert shield_rule_groups['label'][2].minscale is None
        assert shield_rule_groups['label'][2].maxscale is None
        self.assertEqual('Helvetica', shield_rule_groups['label'][2].symbolizers[0].face_name)
        self.assertEqual(14, shield_rule_groups['label'][2].symbolizers[0].size)
        if not MAPNIK_AUTO_IMAGE_SUPPORT:
            self.assertEqual(8, shield_rule_groups['label'][2].symbolizers[0].width)
            self.assertEqual(8, shield_rule_groups['label'][2].symbolizers[0].height)
        self.assertEqual("[bar] = 'baz' and [foo] <= 1", shield_rule_groups['label'][2].filter.text)
        
        assert shield_rule_groups['label'][3].minscale is None
        assert shield_rule_groups['label'][3].maxscale is None
        self.assertEqual('Helvetica', shield_rule_groups['label'][3].symbolizers[0].face_name)
        self.assertEqual(14, shield_rule_groups['label'][3].symbolizers[0].size)
        if not MAPNIK_AUTO_IMAGE_SUPPORT:
            self.assertEqual(8, shield_rule_groups['label'][3].symbolizers[0].width)
            self.assertEqual(8, shield_rule_groups['label'][3].symbolizers[0].height)
        self.assertEqual("[bar] = 'baz' and [foo] > 1", shield_rule_groups['label'][3].filter.text)
        
        assert shield_rule_groups['label'][4].minscale is None
        assert shield_rule_groups['label'][4].maxscale is None
        self.assertEqual('Helvetica', shield_rule_groups['label'][4].symbolizers[0].face_name)
        self.assertEqual(16, shield_rule_groups['label'][4].symbolizers[0].size)
        if not MAPNIK_AUTO_IMAGE_SUPPORT:
            self.assertEqual(8, shield_rule_groups['label'][4].symbolizers[0].width)
            self.assertEqual(8, shield_rule_groups['label'][4].symbolizers[0].height)
        self.assertEqual("[bar] = 'quux' and [foo] <= 1", shield_rule_groups['label'][4].filter.text)
        
        assert shield_rule_groups['label'][5].minscale is None
        assert shield_rule_groups['label'][5].maxscale is None
        self.assertEqual('Helvetica', shield_rule_groups['label'][5].symbolizers[0].face_name)
        self.assertEqual(16, shield_rule_groups['label'][5].symbolizers[0].size)
        if not MAPNIK_AUTO_IMAGE_SUPPORT:
            self.assertEqual(8, shield_rule_groups['label'][5].symbolizers[0].width)
            self.assertEqual(8, shield_rule_groups['label'][5].symbolizers[0].height)
        self.assertEqual("[bar] = 'quux' and [foo] > 1", shield_rule_groups['label'][5].filter.text)

        point_rules = get_point_rules(declarations, target_dir=self.tmpdir)
        
        assert point_rules[0].filter is None
        assert point_rules[0].minscale is None
        assert point_rules[0].maxscale is None
        if not MAPNIK_AUTO_IMAGE_SUPPORT:
            self.assertEqual('png', point_rules[0].symbolizers[0].type)
            self.assertEqual(8, point_rules[0].symbolizers[0].width)
            self.assertEqual(8, point_rules[0].symbolizers[0].height)

    def testStyleRules07(self):
        s = """
            Layer { point-file: url('http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png'); }
            Layer { polygon-pattern-file: url('http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png'); }
            Layer { line-pattern-file: url('http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png'); }
        """
    
        declarations = stylesheet_declarations(s, is_gym=True)

        point_rules = get_point_rules(declarations, target_dir=self.tmpdir)
        
        assert point_rules[0].filter is None
        assert point_rules[0].minscale is None
        assert point_rules[0].maxscale is None
        if not MAPNIK_AUTO_IMAGE_SUPPORT:
            self.assertEqual('png', point_rules[0].symbolizers[0].type)
            self.assertEqual(8, point_rules[0].symbolizers[0].width)
            self.assertEqual(8, point_rules[0].symbolizers[0].height)

        polygon_pattern_rules = get_polygon_pattern_rules(declarations, target_dir=self.tmpdir)
        
        assert polygon_pattern_rules[0].filter is None
        assert polygon_pattern_rules[0].minscale is None
        assert polygon_pattern_rules[0].maxscale is None
        if not MAPNIK_AUTO_IMAGE_SUPPORT:
            self.assertEqual('png', polygon_pattern_rules[0].symbolizers[0].type)
            self.assertEqual(8, polygon_pattern_rules[0].symbolizers[0].width)
            self.assertEqual(8, polygon_pattern_rules[0].symbolizers[0].height)

        line_pattern_rules = get_line_pattern_rules(declarations, target_dir=self.tmpdir)
        
        assert line_pattern_rules[0].filter is None
        assert line_pattern_rules[0].minscale is None
        assert line_pattern_rules[0].maxscale is None
        if not MAPNIK_AUTO_IMAGE_SUPPORT:
            self.assertEqual('png', line_pattern_rules[0].symbolizers[0].type)
            self.assertEqual(8, line_pattern_rules[0].symbolizers[0].width)
            self.assertEqual(8, line_pattern_rules[0].symbolizers[0].height)

    def testStyleRules08(self):
        s = """
            Layer { line-width: 3; line-color: #fff; }
            Layer[foo=1] { outline-width: 1; outline-color: #000; }
            Layer[bar=1] { inline-width: 1; inline-color: #999; }
        """
    
        declarations = stylesheet_declarations(s, is_gym=True)
        
        line_rules = get_line_rules(declarations, target_dir=self.tmpdir)
        
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
    
        declarations = stylesheet_declarations(s, is_gym=True)
        
        line_rules = get_line_rules(declarations, target_dir=self.tmpdir)
        
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
    
        declarations = stylesheet_declarations(s, is_gym=True)
        
        polygon_rules = get_polygon_rules(declarations, target_dir=self.tmpdir)
        
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
        """ Spaces in attribute selectors need to be acceptable
        """
        s = """
            Layer[PERSONS < 2000000] { polygon-fill: #6CAE4C; }
            Layer[PERSONS >= 2000000][PERSONS < 4000000] { polygon-fill: #3B7AB3; }
            Layer[PERSONS > 4000000] { polygon-fill: #88000F; }
        """
    
        declarations = stylesheet_declarations(s)
        polygon_rules = get_polygon_rules(declarations, target_dir=self.tmpdir)
        
        self.assertEqual("[PERSONS] < 2000000", polygon_rules[0].filter.text)
        self.assertEqual(color(0x6c, 0xae, 0x4c), polygon_rules[0].symbolizers[0].color)
        
        self.assertEqual("[PERSONS] >= 2000000 and [PERSONS] < 4000000", polygon_rules[1].filter.text)
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

        declarations = stylesheet_declarations(s, is_gym=True)

        polygon_rules = get_polygon_rules(declarations, target_dir=self.tmpdir)
        
        self.assertEqual(color(0x00, 0x00, 0x00), polygon_rules[0].symbolizers[0].color)
        self.assertEqual(0.5, polygon_rules[0].symbolizers[0].opacity)

        line_rules = get_line_rules(declarations, target_dir=self.tmpdir)
        
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

        declarations = stylesheet_declarations(s, is_gym=True)

        text_rule_groups = get_text_rule_groups(declarations)
        
        self.assertEqual('Helvetica', text_rule_groups['label'][0].symbolizers[0].face_name)
        self.assertEqual('Helvetica', text_rule_groups['label'][0].symbolizers[0].face_name)
        self.assertEqual(12, text_rule_groups['label'][0].symbolizers[0].size)

        self.assertEqual(color(0xFF, 0x00, 0x00), text_rule_groups['label'][0].symbolizers[0].color)
        self.assertEqual(100, text_rule_groups['label'][0].symbolizers[0].wrap_width)
        self.assertEqual(50, text_rule_groups['label'][0].symbolizers[0].spacing)
        self.assertEqual(25, text_rule_groups['label'][0].symbolizers[0].label_position_tolerance)
        self.assertEqual(10, text_rule_groups['label'][0].symbolizers[0].max_char_angle_delta)
        self.assertEqual(color(0xFF, 0xFF, 0x00), text_rule_groups['label'][0].symbolizers[0].halo_color)
        self.assertEqual(2, text_rule_groups['label'][0].symbolizers[0].halo_radius)
        self.assertEqual(10, text_rule_groups['label'][0].symbolizers[0].dx)
        self.assertEqual(15, text_rule_groups['label'][0].symbolizers[0].dy)
        self.assertEqual(boolean(1), text_rule_groups['label'][0].symbolizers[0].avoid_edges)
        self.assertEqual(5, text_rule_groups['label'][0].symbolizers[0].min_distance)
        self.assertEqual(boolean(0), text_rule_groups['label'][0].symbolizers[0].allow_overlap)
        self.assertEqual('point', text_rule_groups['label'][0].symbolizers[0].placement)

    def testStyleRules12a(self):
        s = """
            Layer label1
            {
                text-face-name: 'Helvetica';
                text-fontset: 'bananas';

                text-size: 12;
                text-fill: #f00;
            }
            Layer label2
            {
                text-fontset: "monkeys";

                text-size: 12;
                text-fill: #f00;
            }
        """

        declarations = stylesheet_declarations(s, is_gym=True)

        text_rule_groups = get_text_rule_groups(declarations)
        
        self.assertEqual('Helvetica', text_rule_groups['label1'][0].symbolizers[0].face_name)
        self.assertEqual('bananas', text_rule_groups['label1'][0].symbolizers[0].fontset)

        self.assertEqual('', text_rule_groups['label2'][0].symbolizers[0].face_name)
        self.assertEqual('monkeys', text_rule_groups['label2'][0].symbolizers[0].fontset)

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

        declarations = stylesheet_declarations(s, is_gym=True)

        point_rules = get_point_rules(declarations, target_dir=self.tmpdir)
        
        self.assertEqual(16, point_rules[0].symbolizers[0].width)
        self.assertEqual(16, point_rules[0].symbolizers[0].height)
        self.assertEqual(boolean(True), point_rules[0].symbolizers[0].allow_overlap)

        polygon_pattern_rules = get_polygon_pattern_rules(declarations, target_dir=self.tmpdir)
        
        self.assertEqual(16, polygon_pattern_rules[0].symbolizers[0].width)
        self.assertEqual(16, polygon_pattern_rules[0].symbolizers[0].height)

        line_pattern_rules = get_line_pattern_rules(declarations, target_dir=self.tmpdir)
        
        self.assertEqual(16, line_pattern_rules[0].symbolizers[0].width)
        self.assertEqual(16, line_pattern_rules[0].symbolizers[0].height)

    def testStyleRules14(self):
        s = """
            Layer just_text
            {
                shield-face-name: 'Helvetica';
                shield-size: 12;
                
                shield-fill: #f00;
                shield-min-distance: 5;
            }

            Layer just_image
            {
                shield-file: url('http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png');
                shield-width: 16;
                shield-height: 16;
                
                shield-min-distance: 5;
            }

            Layer both
            {
                shield-fontset: 'SuperFonts';
                shield-size: 12;
                
                shield-file: url('http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png');
                shield-width: 16;
                shield-height: 16;
                
                shield-fill: #f00;
                shield-min-distance: 5;
            }
        """

        declarations = stylesheet_declarations(s, is_gym=True)

        shield_rule_groups = get_shield_rule_groups(declarations, target_dir=self.tmpdir)
        
        self.assertEqual('Helvetica', shield_rule_groups['just_text'][0].symbolizers[0].face_name)
        self.assertEqual(12, shield_rule_groups['just_text'][0].symbolizers[0].size)
        self.assertEqual(color(0xFF, 0x00, 0x00), shield_rule_groups['just_text'][0].symbolizers[0].color)
        self.assertEqual(5, shield_rule_groups['just_text'][0].symbolizers[0].min_distance)

        self.assertEqual(16, shield_rule_groups['just_image'][0].symbolizers[0].width)
        self.assertEqual(16, shield_rule_groups['just_image'][0].symbolizers[0].height)
        self.assertEqual(5, shield_rule_groups['just_image'][0].symbolizers[0].min_distance)
        
        self.assertEqual('', shield_rule_groups['both'][0].symbolizers[0].face_name)
        self.assertEqual('SuperFonts', shield_rule_groups['both'][0].symbolizers[0].fontset)
        self.assertEqual(12, shield_rule_groups['both'][0].symbolizers[0].size)
        self.assertEqual(color(0xFF, 0x00, 0x00), shield_rule_groups['both'][0].symbolizers[0].color)
        self.assertEqual(16, shield_rule_groups['both'][0].symbolizers[0].width)
        self.assertEqual(16, shield_rule_groups['both'][0].symbolizers[0].height)
        self.assertEqual(5, shield_rule_groups['both'][0].symbolizers[0].min_distance)

class DataSourcesTests(unittest.TestCase):

    def gen_section(self, name, **kwargs):
        return """[%s]\n%s""" % (name, "\n".join(("%s=%s" % kwarg for kwarg in kwargs.items())))

    def testSimple1(self):
        cdata = """
[simple]
type=shape
file=foo.shp
garbage=junk
"""
        dss = DataSources()
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
        dss = DataSources()
        dss.add_config(self.gen_section("t1", type="shape", file="foo"), __file__)
        dss.add_config(self.gen_section("t2", type="shape", file="foo"), __file__)
        self.assertTrue(dss.get('t1') != None)
        self.assertTrue(dss.get('t2') != None)

    def testDefaults1(self):
        dss = DataSources()
        dss.add_config(self.gen_section("DEFAULT", var="cows"), __file__)
        dss.add_config(self.gen_section("t1", type="shape", file="%(var)s"), __file__)

        self.assertEqual(dss.get('t1')['parameters']['file'], "cows")

    def testChainedDefaults1(self):
        dss = DataSources()
        dss.add_config(self.gen_section("DEFAULT", var="cows"), __file__)
        dss.add_config(self.gen_section("DEFAULT", var="cows2"), __file__)
        dss.add_config(self.gen_section("t1", type="shape", file="%(var)s"), __file__)

        self.assertEqual(dss.get('t1')['parameters']['file'], "cows2")

    def testBase1(self):
        dss = DataSources()
        dss.add_config(self.gen_section("base", type="shape", encoding="latin1"), __file__)
        dss.add_config(self.gen_section("t2", base="base", file="foo"), __file__)
        self.assertTrue("base" in dss.bases)
        self.assertEqual(dss.get('t2')['base'], 'base')
        self.assertEqual(dss.get('t2')['parameters']['file'], 'foo')

    def testSRS(self):
        dss = DataSources()
        dss.add_config(self.gen_section("s", type="shape", layer_srs="epsg:4326"), __file__)
        dss.add_config(self.gen_section("g", type="shape", layer_srs="epsg:900913"), __file__)
        self.assertEqual(dss.get("s")['layer_srs'], dss.PROJ4_PROJECTIONS['epsg:4326'])
        self.assertEqual(dss.get("g")['layer_srs'], dss.PROJ4_PROJECTIONS['epsg:900913'])
        self.assertRaises(Exception, dss.add_config, (self.gen_section("s", type="shape", layer_srs="epsg:43223432423"), __file__))

    def testDataTypes(self):
        dss = DataSources()
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

    def tearDown(self):
        # destroy the above-created directory
        shutil.rmtree(self.tmpdir)

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
                <Layer>
                    <Datasource>
                        <Parameter name="type">shape</Parameter>
                        <Parameter name="file">data/test.shp</Parameter>
                    </Datasource>
                </Layer>
            </Map>
        """
        map = compile(s, dir=self.tmpdir)
        
        self.assertEqual(1, len(map.layers))
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

        self.assertEqual('Comic Sans', map.layers[0].styles[2].rules[0].symbolizers[0].face_name)
        self.assertEqual(14, map.layers[0].styles[2].rules[0].symbolizers[0].size)

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
                        <Parameter name="file">data/test.shp</Parameter>
                    </Datasource>
                </Layer>
            </Map>
        """
        map = compile(s, dir=self.tmpdir)
        
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
        for k,v in dict(type="shape", file="data/test.shp", encoding="latin1").items():
            self.assertEqual(params[k], v)

    def testCompile3(self):
        """
        """
        map = output.Map(layers=[
            output.Layer('this',
            output.Datasource(type="shape",file="data/test.shp"), [
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
            output.Datasource(type="shape",file="data/test.shp"), [
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
                        line-dasharray: 8,100;
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
                        <Parameter name="file">data/test.shp</Parameter>
                    </Datasource>
                </Layer>
            </Map>
        """
        mmap = mapnik.Map(640, 480)
        ms = compile(s, target_dir=self.tmpdir)
        ms.to_mapnik(mmap)
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
                        <Parameter name="file">data/test.shp</Parameter>
                    </Datasource>
                </Layer>
            </Map>
        """.encode('utf-8')
        mmap = mapnik.Map(640, 480)
        ms = compile(s, target_dir=self.tmpdir)
        ms.to_mapnik(mmap)
        mapnik.save_map(mmap, os.path.join(self.tmpdir, 'out.mml'))
        
        
if __name__ == '__main__':
    unittest.main()
