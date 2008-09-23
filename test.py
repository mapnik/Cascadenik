import sys
import unittest
from style import ParseException, parse_stylesheet, unroll_rulesets
from style import Selector, SelectorElement, SelectorAttributeTest
from style import postprocess_property, postprocess_value, Property
from compile import selectors_filters

class ParseTests(unittest.TestCase):
    
    def testBadSelector1(self):
        self.assertRaises(ParseException, parse_stylesheet, 'Too Many Things { }')

    def testBadSelector2(self):
        self.assertRaises(ParseException, parse_stylesheet, '{ }')

    def testBadSelector3(self):
        self.assertRaises(ParseException, parse_stylesheet, 'Illegal { }')

    def testBadSelector4(self):
        self.assertRaises(ParseException, parse_stylesheet, 'Layer foo[this=that] { }')

    def testBadSelector5(self):
        self.assertRaises(ParseException, parse_stylesheet, 'Layer[this>that] foo { }')

    def testBadSelector6(self):
        self.assertRaises(ParseException, parse_stylesheet, 'Layer foo#bar { }')

    def testBadSelector7(self):
        self.assertRaises(ParseException, parse_stylesheet, 'Layer foo.bar { }')

    def testBadSelectorTest1(self):
        self.assertRaises(ParseException, parse_stylesheet, 'Layer[foo>] { }')

    def testBadSelectorTest2(self):
        self.assertRaises(ParseException, parse_stylesheet, 'Layer[foo><bar] { }')

    def testBadSelectorTest3(self):
        self.assertRaises(ParseException, parse_stylesheet, 'Layer[foo<<bar] { }')

    def testBadSelectorTest4(self):
        self.assertRaises(ParseException, parse_stylesheet, 'Layer[<bar] { }')

    def testBadSelectorTest5(self):
        self.assertRaises(ParseException, parse_stylesheet, 'Layer[<<bar] { }')

    def testBadProperty1(self):
        self.assertRaises(ParseException, parse_stylesheet, 'Layer { unknown-property: none; }')

    def testBadProperty2(self):
        self.assertRaises(ParseException, parse_stylesheet, 'Layer { extra thing: none; }')

    def testBadProperty3(self):
        self.assertRaises(ParseException, parse_stylesheet, 'Layer { "not an ident": none; }')

    def testRulesets1(self):
        self.assertEqual(0, len(parse_stylesheet('/* empty stylesheet */')))

    def testRulesets2(self):
        self.assertEqual(1, len(parse_stylesheet('Layer { }')))

    def testRulesets3(self):
        self.assertEqual(2, len(parse_stylesheet('Layer { } Layer { }')))

    def testRulesets4(self):
        self.assertEqual(3, len(parse_stylesheet('Layer { } /* something */ Layer { } /* extra */ Layer { }')))

    def testRulesets5(self):
        self.assertEqual(1, len(parse_stylesheet('Map { }')))

class SelectorTests(unittest.TestCase):
    
    def testSpecificity1(self):
        self.assertEquals((0, 1, 0), Selector(SelectorElement(['Layer'])).specificity())
    
    def testSpecificity2(self):
        self.assertEquals((0, 2, 0), Selector(SelectorElement(['Layer']), SelectorElement(['name'])).specificity())
    
    def testSpecificity3(self):
        self.assertEquals((0, 2, 0), Selector(SelectorElement(['Layer', '.class'])).specificity())
    
    def testSpecificity4(self):
        self.assertEquals((0, 3, 0), Selector(SelectorElement(['Layer', '.class']), SelectorElement(['name'])).specificity())
    
    def testSpecificity5(self):
        self.assertEquals((1, 2, 0), Selector(SelectorElement(['Layer', '#id']), SelectorElement(['name'])).specificity())
    
    def testSpecificity6(self):
        self.assertEquals((1, 0, 0), Selector(SelectorElement(['#id'])).specificity())
    
    def testSpecificity7(self):
        self.assertEquals((1, 0, 1), Selector(SelectorElement(['#id'], [SelectorAttributeTest('a', '>', 'b')])).specificity())
    
    def testSpecificity8(self):
        self.assertEquals((1, 0, 2), Selector(SelectorElement(['#id'], [SelectorAttributeTest('a', '>', 'b'), SelectorAttributeTest('a', '<', 'b')])).specificity())

    def testSpecificity9(self):
        self.assertEquals((1, 0, 2), Selector(SelectorElement(['#id'], [SelectorAttributeTest('a', '>', 100), SelectorAttributeTest('a', '<', 'b')])).specificity())

    def testMatch1(self):
        self.assertEqual(True, Selector(SelectorElement(['Layer'])).matches('Layer', 'foo', []))

    def testMatch2(self):
        self.assertEqual(True, Selector(SelectorElement(['#foo'])).matches('Layer', 'foo', []))

    def testMatch3(self):
        self.assertEqual(False, Selector(SelectorElement(['#foo'])).matches('Layer', 'bar', []))

    def testMatch4(self):
        self.assertEqual(True, Selector(SelectorElement(['.bar'])).matches('Layer', None, ['bar']))

    def testMatch5(self):
        self.assertEqual(True, Selector(SelectorElement(['.bar'])).matches('Layer', None, ['bar', 'baz']))

    def testMatch6(self):
        self.assertEqual(True, Selector(SelectorElement(['.bar', '.baz'])).matches('Layer', None, ['bar', 'baz']))

    def testMatch7(self):
        self.assertEqual(False, Selector(SelectorElement(['.bar', '.baz'])).matches('Layer', None, ['bar']))

    def testMatch8(self):
        self.assertEqual(False, Selector(SelectorElement(['Layer'])).matches('Map', None, []))

    def testMatch9(self):
        self.assertEqual(False, Selector(SelectorElement(['Map'])).matches('Layer', None, []))

    def testMatch10(self):
        self.assertEqual(True, Selector(SelectorElement(['*'])).matches('Layer', None, []))

    def testMatch10(self):
        self.assertEqual(True, Selector(SelectorElement(['*'])).matches('Map', None, []))

    def testRange1(self):
        selector = Selector(SelectorElement(['*'], [SelectorAttributeTest('scale-denominator', '>', 100)]))
        self.assertEqual(True, selector.isRanged())
        self.assertEqual(False, selector.inRange(99))
        self.assertEqual(False, selector.inRange(100))
        self.assertEqual(True, selector.inRange(1000))

    def testRange2(self):
        selector = Selector(SelectorElement(['*'], [SelectorAttributeTest('scale-denominator', '>=', 100)]))
        self.assertEqual(True, selector.isRanged())
        self.assertEqual(False, selector.inRange(99))
        self.assertEqual(True, selector.inRange(100))
        self.assertEqual(True, selector.inRange(1000))

    def testRange3(self):
        selector = Selector(SelectorElement(['*'], [SelectorAttributeTest('scale-denominator', '<', 100)]))
        self.assertEqual(True, selector.isRanged())
        self.assertEqual(True, selector.inRange(99))
        self.assertEqual(False, selector.inRange(100))
        self.assertEqual(False, selector.inRange(1000))

    def testRange4(self):
        selector = Selector(SelectorElement(['*'], [SelectorAttributeTest('scale-denominator', '<=', 100)]))
        self.assertEqual(True, selector.isRanged())
        self.assertEqual(True, selector.inRange(99))
        self.assertEqual(True, selector.inRange(100))
        self.assertEqual(False, selector.inRange(1000))

    def testRange5(self):
        selector = Selector(SelectorElement(['*'], [SelectorAttributeTest('nonsense', '<=', 100)]))
        self.assertEqual(False, selector.isRanged())
        self.assertEqual(True, selector.inRange(99))
        self.assertEqual(True, selector.inRange(100))
        self.assertEqual(True, selector.inRange(1000))

    def testRange6(self):
        selector = Selector(SelectorElement(['*'], [SelectorAttributeTest('scale-denominator', '>=', 100), SelectorAttributeTest('scale-denominator', '<', 1000)]))
        self.assertEqual(True, selector.isRanged())
        self.assertEqual(False, selector.inRange(99))
        self.assertEqual(True, selector.inRange(100))
        self.assertEqual(False, selector.inRange(1000))

    def testRange7(self):
        selector = Selector(SelectorElement(['*'], [SelectorAttributeTest('scale-denominator', '>', 100), SelectorAttributeTest('scale-denominator', '<=', 1000)]))
        self.assertEqual(True, selector.isRanged())
        self.assertEqual(False, selector.inRange(99))
        self.assertEqual(False, selector.inRange(100))
        self.assertEqual(True, selector.inRange(1000))

    def testRange8(self):
        selector = Selector(SelectorElement(['*'], [SelectorAttributeTest('scale-denominator', '<=', 100), SelectorAttributeTest('scale-denominator', '>=', 1000)]))
        self.assertEqual(True, selector.isRanged())
        self.assertEqual(False, selector.inRange(99))
        self.assertEqual(False, selector.inRange(100))
        self.assertEqual(False, selector.inRange(1000))

class PropertyTests(unittest.TestCase):

    def testProperty1(self):
        self.assertRaises(ParseException, postprocess_property, [('IDENT', 'too-many'), ('IDENT', 'properties')])

    def testProperty2(self):
        self.assertRaises(ParseException, postprocess_property, [])

    def testProperty3(self):
        self.assertRaises(ParseException, postprocess_property, [('IDENT', 'illegal-property')])

    def testProperty4(self):
        self.assertEquals('shield', postprocess_property([('IDENT', 'shield-fill')]).group())

    def testProperty5(self):
        self.assertEquals('shield', postprocess_property([('S', ' '), ('IDENT', 'shield-fill'), ('COMMENT', 'ignored comment')]).group())

class ValueTests(unittest.TestCase):

    def testBadValue1(self):
        self.assertRaises(ParseException, postprocess_value, [], Property('polygon-opacity'))

    def testBadValue2(self):
        self.assertRaises(ParseException, postprocess_value, [('IDENT', 'too'), ('IDENT', 'many')], Property('polygon-opacity'))

    def testBadValue3(self):
        self.assertRaises(ParseException, postprocess_value, [('IDENT', 'non-number')], Property('polygon-opacity'))

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

class CascadeTests(unittest.TestCase):

    def testCascade1(self):
        s = """
            Layer
            {
                text-dx: -10;
                text-dy: -10;
            }
        """
        rulesets = parse_stylesheet(s)
        
        self.assertEqual(1, len(rulesets))
        self.assertEqual(1, len(rulesets[0]['selectors']))
        self.assertEqual(1, len(rulesets[0]['selectors'][0].elements))

        self.assertEqual(2, len(rulesets[0]['declarations']))
        self.assertEqual('text-dx', rulesets[0]['declarations'][0]['property'].name)
        self.assertEqual(-10, rulesets[0]['declarations'][0]['value'].value)
        
        declarations = unroll_rulesets(rulesets)
        
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
            }
        """
        rulesets = parse_stylesheet(s)
        
        self.assertEqual(2, len(rulesets))
        self.assertEqual(1, len(rulesets[0]['selectors']))
        self.assertEqual(1, len(rulesets[0]['selectors'][0].elements))
        self.assertEqual(2, len(rulesets[1]['selectors']))
        self.assertEqual(2, len(rulesets[1]['selectors'][0].elements))
        self.assertEqual(1, len(rulesets[1]['selectors'][1].elements))
        
        declarations = unroll_rulesets(rulesets)

        self.assertEqual(15, len(declarations))

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

        self.assertEqual('Layer#foo.foo[baz>10] bar', str(declarations[7].selector))
        self.assertEqual('polygon-fill', declarations[7].property.name)
        self.assertEqual('#ff9900', str(declarations[7].value))

        self.assertEqual('Layer#foo.foo[baz>10] bar', str(declarations[8].selector))
        self.assertEqual('text-face-name', declarations[8].property.name)
        self.assertEqual('Helvetica Bold', str(declarations[8].value))

        self.assertEqual('Layer#foo.foo[baz>10] bar', str(declarations[9].selector))
        self.assertEqual('text-size', declarations[9].property.name)
        self.assertEqual('10', str(declarations[9].value))

        self.assertEqual('Layer#foo.foo[baz>10] bar', str(declarations[10].selector))
        self.assertEqual('polygon-pattern-file', declarations[10].property.name)
        self.assertEqual('http://example.com', str(declarations[10].value))

        self.assertEqual('Layer#foo.foo[baz>10] bar', str(declarations[11].selector))
        self.assertEqual('line-cap', declarations[11].property.name)
        self.assertEqual('square', str(declarations[11].value))

        self.assertEqual('Layer#foo.foo[baz>10] bar', str(declarations[12].selector))
        self.assertEqual('text-allow-overlap', declarations[12].property.name)
        self.assertEqual('false', str(declarations[12].value))

        self.assertEqual('Layer#foo.foo[baz>10] bar', str(declarations[13].selector))
        self.assertEqual('text-dx', declarations[13].property.name)
        self.assertEqual('-10', str(declarations[13].value))

        self.assertEqual('*', str(declarations[14].selector))
        self.assertEqual('text-fill', declarations[14].property.name)
        self.assertEqual('#ff9900', str(declarations[14].value))

class FilterCombinationTests(unittest.TestCase):

    def testFilters1(self):
        s = """
            Layer[landuse=military]     { polygon-fill: #000; }
            Layer[landuse=civilian]     { polygon-fill: #001; }
            Layer[landuse=agriculture]  { polygon-fill: #010; }
        """
        rulesets = parse_stylesheet(s)
        selectors = [dec.selector for dec in unroll_rulesets(rulesets)]
        filters = selectors_filters(selectors)
        
        self.assertEqual(len(filters), 4)
        self.assertEqual(str(sorted(filters)), '[[landuse!=agriculture][landuse!=civilian][landuse!=military], [landuse=agriculture], [landuse=civilian], [landuse=military]]')

    def testFilters2(self):
        s = """
            Layer[landuse=military]     { polygon-fill: #000; }
            Layer[landuse=civilian]     { polygon-fill: #001; }
            Layer[landuse=agriculture]  { polygon-fill: #010; }
            Layer[horse=yes]    { polygon-fill: #011; }
        """
        rulesets = parse_stylesheet(s)
        selectors = [dec.selector for dec in unroll_rulesets(rulesets)]
        filters = selectors_filters(selectors)
        
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
        rulesets = parse_stylesheet(s)
        selectors = [dec.selector for dec in unroll_rulesets(rulesets)]
        filters = selectors_filters(selectors)
        
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
        rulesets = parse_stylesheet(s)
        selectors = [dec.selector for dec in unroll_rulesets(rulesets)]
        filters = selectors_filters(selectors)
        
        self.assertEqual(len(filters), 16)
        self.assertEqual(str(sorted(filters)), '[[horse!=yes][landuse!=agriculture][landuse!=civilian][landuse!=military][leisure!=park], [horse!=yes][landuse!=agriculture][landuse!=civilian][landuse!=military][leisure=park], [horse!=yes][landuse=agriculture][leisure!=park], [horse!=yes][landuse=agriculture][leisure=park], [horse!=yes][landuse=civilian][leisure!=park], [horse!=yes][landuse=civilian][leisure=park], [horse!=yes][landuse=military][leisure!=park], [horse!=yes][landuse=military][leisure=park], [horse=yes][landuse!=agriculture][landuse!=civilian][landuse!=military][leisure!=park], [horse=yes][landuse!=agriculture][landuse!=civilian][landuse!=military][leisure=park], [horse=yes][landuse=agriculture][leisure!=park], [horse=yes][landuse=agriculture][leisure=park], [horse=yes][landuse=civilian][leisure!=park], [horse=yes][landuse=civilian][leisure=park], [horse=yes][landuse=military][leisure!=park], [horse=yes][landuse=military][leisure=park]]')

if __name__ == '__main__':
    unittest.main()
