import sys
from re import sub
from itertools import count
from os import getcwd, chdir

from . import style, mapnik, MAPNIK_VERSION

def safe_str(s):
    return None if not s else unicode(s).encode('utf-8')

def fontset_name(face_names):
    return '-'.join([sub(r'\W', '_', name) for name in face_names])

class OutputException(Exception):
    """ Exception raised when an output error is encountered.
    """
    pass

class Map:
    def __init__(self, srs=None, layers=None, background=None):
        assert srs is None or isinstance(srs, basestring)
        assert layers is None or type(layers) in (list, tuple)
        assert background is None or background.__class__ is style.color or background == 'transparent'
        
        self.srs = safe_str(srs)
        self.layers = layers or []
        self.background = background

    def __repr__(self):
        return 'Map(%s %s)' % (self.background, repr(self.layers))

    def to_mapnik(self, mmap, dirs=None):
        """
        """
        prev_cwd = getcwd()
        
        if dirs:
            chdir(dirs.output)
        
        try:
            mmap.srs = self.srs or mmap.srs
            if self.background:
                mmap.background = mapnik.Color(str(self.background))
            
            ids = count(1)
            fontsets = dict()
            
            for layer in self.layers:
                for style in layer.styles:
    
                    sty = mapnik.Style()
                    
                    if MAPNIK_VERSION >= 200000:
                        sty.filter_mode = mapnik.filter_mode.FIRST
                    
                    for rule in style.rules:
                        rul = mapnik.Rule('rule %d' % ids.next())
                        rul.filter = rule.filter and mapnik.Filter(rule.filter.text) or rul.filter
                        rul.min_scale = rule.minscale and rule.minscale.value or rul.min_scale
                        rul.max_scale = rule.maxscale and rule.maxscale.value or rul.max_scale
                        
                        for symbolizer in rule.symbolizers:
                            if not hasattr(symbolizer, 'to_mapnik'):
                                continue
    
                            if hasattr(symbolizer, 'get_fontset_name'):
                                fontset_name = symbolizer.get_fontset_name()
                            
                                if fontset_name and fontset_name not in fontsets:
                                    fontset = FontSet(symbolizer.face_name.values).to_mapnik()
                                    mmap.append_fontset(fontset_name, fontset)
                                    fontsets[fontset_name] = mmap.find_fontset(fontset_name)

                                sym = symbolizer.to_mapnik(fontsets)
                            
                            else:
                                sym = symbolizer.to_mapnik()
                            
                            rul.symbols.append(sym)
                        sty.rules.append(rul)
                    mmap.append_style(style.name, sty)
    
                lay = mapnik.Layer(layer.name)
                lay.srs = layer.srs or lay.srs
                if layer.datasource:
                    lay.datasource = layer.datasource.to_mapnik()
                lay.minzoom = layer.minzoom or lay.minzoom
                lay.maxzoom = layer.maxzoom or lay.maxzoom
                
                for style in layer.styles:
                    lay.styles.append(style.name)
    
                mmap.layers.append(lay)
        
        except:
            # pass it along, but first chdir back to the previous directory
            # in the finally clause below, to put things back the way they were.
            raise
        
        finally:
            chdir(prev_cwd)

class Style:
    def __init__(self, name, rules):
        assert name is None or type(name) is str
        assert rules is None or type(rules) in (list, tuple)
        
        self.name = name
        self.rules = rules or []

    def __repr__(self):
        return 'Style(%s: %s)' % (self.name, repr(self.rules))

class Rule:
    def __init__(self, minscale, maxscale, filter, symbolizers):
        assert minscale is None or minscale.__class__ is MinScaleDenominator
        assert maxscale is None or maxscale.__class__ is MaxScaleDenominator
        assert filter is None or filter.__class__ is Filter

        self.minscale = minscale
        self.maxscale = maxscale
        self.filter = filter
        self.symbolizers = symbolizers

    def __repr__(self):
        return 'Rule(%s:%s, %s, %s)' % (repr(self.minscale), repr(self.maxscale), repr(self.filter), repr(self.symbolizers))

class Layer:
    def __init__(self, name, datasource, styles=None, srs=None, minzoom=None, maxzoom=None):
        assert isinstance(name, basestring)
        assert styles is None or type(styles) in (list, tuple)
        assert srs is None or isinstance(srs, basestring)
        assert minzoom is None or type(minzoom) in (int, float)
        assert maxzoom is None or type(maxzoom) in (int, float)
        
        self.name = safe_str(name)
        self.datasource = datasource
        self.styles = styles or []
        self.srs = safe_str(srs)
        self.minzoom = minzoom
        self.maxzoom = maxzoom

    def __repr__(self):
        return 'Layer(%s: %s)' % (self.name, repr(self.styles))

class Datasource:
    def __init__(self, **parameters):
        self.parameters = {}
        for param, value in parameters.items():
            if isinstance(value, basestring):
                value = safe_str(value)
            self.parameters[param] = value

    def to_mapnik(self):
        return mapnik.Datasource(**self.parameters)

class MinScaleDenominator:
    def __init__(self, value):
        assert type(value) is int
        self.value = value

    def __repr__(self):
        return str(self.value)

class MaxScaleDenominator:
    def __init__(self, value):
        assert type(value) is int
        self.value = value

    def __repr__(self):
        return str(self.value)

class Filter:
    def __init__(self, text):
        self.text = text.encode('utf8')
    
    def __repr__(self):
        return str(self.text)

class PolygonSymbolizer:
    def __init__(self, color, opacity=None, gamma=None):
        assert color.__class__ is style.color
        assert opacity is None or type(opacity) in (int, float)
        assert gamma is None or type(gamma) in (int, float)

        self.color = color
        self.opacity = opacity or 1.0
        self.gamma = gamma

    def __repr__(self):
        return 'Polygon(%s, %s, %s)' % (self.color, self.opacity, self.gamma)

    def to_mapnik(self):
        sym = mapnik.PolygonSymbolizer(mapnik.Color(str(self.color)))
        sym.fill_opacity = self.opacity
        sym.gamma = self.gamma or sym.gamma
        
        return sym

class RasterSymbolizer:
    def __init__(self, mode=None, opacity=None, scaling=None):
        assert opacity is None or type(opacity) in (int, float)
        assert mode is None or isinstance(mode, basestring)
        assert scaling is None or isinstance(scaling, basestring)

        self.mode = safe_str(mode)
        self.opacity = opacity or 1.0
        self.scaling = safe_str(scaling)

    def __repr__(self):
        return 'Raster(%s, %s, %s)' % (self.mode, self.opacity, self.scaling)

    def to_mapnik(self):
        sym = mapnik.RasterSymbolizer()
        sym.opacity = self.opacity
        sym.mode = self.mode or sym.mode
        sym.scaling = self.scaling or sym.scaling

        return sym

class LineSymbolizer:
    def __init__(self, color, width, opacity=None, join=None, cap=None, dashes=None):
        assert color.__class__ is style.color
        assert type(width) in (int, float)
        assert opacity is None or type(opacity) in (int, float)
        assert join is None or isinstance(join, basestring)
        assert cap is None or isinstance(cap, basestring)
        assert dashes is None or dashes.__class__ is style.numbers

        self.color = color
        self.width = width
        self.opacity = opacity
        self.join = safe_str(join)
        self.cap = safe_str(cap)
        self.dashes = dashes

    def __repr__(self):
        return 'Line(%s, %s)' % (self.color, self.width)

    def to_mapnik(self):
        line_caps = {'butt': mapnik.line_cap.BUTT_CAP,
                     'round': mapnik.line_cap.ROUND_CAP,
                     'square': mapnik.line_cap.SQUARE_CAP}

        line_joins = {'miter': mapnik.line_join.MITER_JOIN,
                      'round': mapnik.line_join.ROUND_JOIN,
                      'bevel': mapnik.line_join.BEVEL_JOIN}
    
        stroke = mapnik.Stroke(mapnik.Color(str(self.color)), self.width)
        stroke.opacity = self.opacity or stroke.opacity
        stroke.line_cap = self.cap and line_caps[self.cap] or stroke.line_cap
        stroke.line_join = self.join and line_joins[self.join] or stroke.line_join

        if self.dashes:
            lengths_gaps = list(self.dashes.values)
            while lengths_gaps:
                (length, gap), lengths_gaps = lengths_gaps[:2], lengths_gaps[2:]
                stroke.add_dash(length, gap)

        sym = mapnik.LineSymbolizer(stroke)
        
        return sym

class FontSet:
    def __init__(self, face_names):
        self.faces = tuple(face_names)
    
    def to_mapnik(self):
        if MAPNIK_VERSION >= 200101:
            fontset = mapnik.FontSet(fontset_name(self.faces))
        else:
            fontset = mapnik.FontSet()
        
        for face in self.faces:
            fontset.add_face_name(face)
        
        return fontset

class TextSymbolizer:
    def __init__(self, name, face_name, size, color, wrap_width=None, \
        label_spacing=None, label_position_tolerance=None, max_char_angle_delta=None, \
        halo_color=None, halo_radius=None, dx=None, dy=None, avoid_edges=None, \
        minimum_distance=None, allow_overlap=None, label_placement=None, \
        character_spacing=None, line_spacing=None, text_transform=None, fontset=None, \
        anchor_dx=None, anchor_dy=None,horizontal_alignment=None,vertical_alignment=None,
        justify_alignment=None, force_odd_labels=None):

        assert isinstance(name, basestring)
        assert face_name is None or face_name.__class__ is style.strings
        assert fontset is None or isinstance(fontset, basestring)
        assert type(size) is int
        assert color.__class__ is style.color
        assert wrap_width is None or type(wrap_width) is int
        assert label_spacing is None or type(label_spacing) is int
        assert label_position_tolerance is None or type(label_position_tolerance) is int
        assert max_char_angle_delta is None or type(max_char_angle_delta) is int
        assert halo_color is None or halo_color.__class__ is style.color
        assert halo_radius is None or type(halo_radius) is int
        assert dx is None or type(dx) is int
        assert dy is None or type(dy) is int
        assert character_spacing is None or type(character_spacing) is int
        assert line_spacing is None or type(line_spacing) is int
        assert avoid_edges is None or avoid_edges.__class__ is style.boolean
        assert minimum_distance is None or type(minimum_distance) is int
        assert allow_overlap is None or allow_overlap.__class__ is style.boolean
        assert label_placement is None or isinstance(label_placement, basestring)
        assert text_transform is None or isinstance(text_transform, basestring)

        assert face_name or fontset, "Must specify either face_name or fontset"

        self.name = safe_str(name)
        self.face_name = face_name
        self.fontset = safe_str(fontset)
        self.size = size
        self.color = color

        self.wrap_width = wrap_width
        self.label_spacing = label_spacing
        self.label_position_tolerance = label_position_tolerance
        self.max_char_angle_delta = max_char_angle_delta
        self.halo_color = halo_color
        self.halo_radius = halo_radius
        self.dx = dx
        self.dy = dy
        self.character_spacing = character_spacing
        self.line_spacing = line_spacing
        self.allow_overlap = allow_overlap
        self.avoid_edges = avoid_edges
        self.minimum_distance = minimum_distance
        self.label_placement = label_placement
        self.text_transform = text_transform
        self.vertical_alignment = vertical_alignment
        self.justify_alignment = justify_alignment
        self.horizontal_alignment = horizontal_alignment
        self.force_odd_labels = force_odd_labels
        self.anchor_dx = anchor_dx
        self.anchor_dy = anchor_dy

    def __repr__(self):
        return 'Text(%s, %s)' % (' '.join(self.face_name.values), self.size)

    def get_fontset_name(self):
        if len(self.face_name.values) > 1 and MAPNIK_VERSION < 200100:
            # Mapnik only supports multiple font face names as of version 2.1
            return None

        if len(self.face_name.values) == 1:
            return None
        
        return fontset_name(self.face_name.values)
    
    def to_mapnik(self, fontsets=None):
        if MAPNIK_VERSION >= 200100:
            convert_enums = {'uppercase': mapnik.text_transform.UPPERCASE,
                             'lowercase': mapnik.text_transform.LOWERCASE}

            if self.get_fontset_name() is not None:
                sym = mapnik.TextSymbolizer(mapnik.Expression('[%s]' % self.name),
                                            '', self.size,
                                            mapnik.Color(str(self.color)))

                sym.fontset = fontsets[self.get_fontset_name()]

            else:
                sym = mapnik.TextSymbolizer(mapnik.Expression('[%s]' % self.name),
                                            self.face_name.values[0], self.size,
                                            mapnik.Color(str(self.color)))

        elif MAPNIK_VERSION >= 200000:
            convert_enums = {'uppercase': mapnik.text_transform.UPPERCASE,
                             'lowercase': mapnik.text_transform.LOWERCASE}

            sym = mapnik.TextSymbolizer(mapnik.Expression('[%s]' % self.name),
                                        self.face_name.values[0], self.size,
                                        mapnik.Color(str(self.color)))
        else:
            # note: these match css in Mapnik2
            convert_enums = {'uppercase': mapnik.text_convert.TOUPPER,
                             'lowercase': mapnik.text_convert.TOLOWER}

            sym = mapnik.TextSymbolizer(self.name, self.face_name.values[0], self.size,
                                        mapnik.Color(str(self.color)))

        sym.wrap_width = self.wrap_width or sym.wrap_width
        sym.label_spacing = self.label_spacing or sym.label_spacing
        sym.label_position_tolerance = self.label_position_tolerance or sym.label_position_tolerance
        
        if MAPNIK_VERSION >= 200100:
            # seriously?
            sym.maximum_angle_char_delta = self.max_char_angle_delta or sym.maximum_angle_char_delta
        else:
            sym.max_char_angle_delta = self.max_char_angle_delta or sym.max_char_angle_delta
        
        sym.halo_fill = mapnik.Color(str(self.halo_color)) if self.halo_color else sym.halo_fill
        sym.halo_radius = self.halo_radius or sym.halo_radius
        sym.character_spacing = self.character_spacing or sym.character_spacing
        sym.line_spacing = self.line_spacing or sym.line_spacing
        sym.avoid_edges = self.avoid_edges.value if self.avoid_edges else sym.avoid_edges
        sym.force_odd_labels = self.force_odd_labels.value if self.force_odd_labels else sym.force_odd_labels
        sym.minimum_distance = self.minimum_distance or sym.minimum_distance
        sym.allow_overlap = self.allow_overlap.value if self.allow_overlap else sym.allow_overlap

        if self.label_placement:
            sym.label_placement = mapnik.label_placement.names.get(self.label_placement,mapnik.label_placement.POINT_PLACEMENT)

        if self.text_transform and MAPNIK_VERSION >= 200000:
            sym.text_convert = convert_enums.get(self.text_transform, mapnik.text_transform.NONE)
        elif self.text_transform:
            # note-renamed in Mapnik2 to 'text_transform'
            sym.text_convert = convert_enums.get(self.text_transform, mapnik.text_convert.NONE)

        if self.vertical_alignment:
            # match the logic in load_map.cpp for conditionally applying vertical_alignment default
            default_vertical_alignment = mapnik.vertical_alignment.MIDDLE
            if self.dx > 0.0:
                default_vertical_alignment = mapnik.vertical_alignment.BOTTOM
            elif self.dy < 0.0:
                default_vertical_alignment = mapnik.vertical_alignment.TOP
            
            sym.vertical_alignment = mapnik.vertical_alignment.names.get(self.vertical_alignment,
                default_vertical_alignment)
        if self.justify_alignment:
            sym.justify_alignment = mapnik.justify_alignment.names.get(self.justify_alignment,
              mapnik.justify_alignment.MIDDLE)

        if self.fontset:
        #    sym.fontset = str(self.fontset)
             # not viable via python
            sys.stderr.write('\nCascadenik debug: Warning, FontSets will be ignored as they are not yet supported in Mapnik via Python...\n')
        
        if MAPNIK_VERSION >= 200000:
            sym.displacement = (self.dx or 0.0, self.dy or 0.0)
        else:
            sym.displacement(self.dx or 0.0, self.dy or 0.0)
        
        return sym

class ShieldSymbolizer:
    def __init__(self, name, face_name=None, size=None, file=None, filetype=None, \
        width=None, height=None, color=None, minimum_distance=None, character_spacing=None, \
        line_spacing=None, label_spacing=None, fontset=None, text_dx=0, text_dy=0):
        
        assert (face_name or fontset) and file
        
        assert isinstance(name, basestring)
        assert face_name is None or face_name.__class__ is style.strings
        assert fontset is None or isinstance(fontset, basestring)
        assert size is None or type(size) is int
        assert width is None or type(width) is int
        assert height is None or type(height) is int

        assert color is None or color.__class__ is style.color
        assert character_spacing is None or type(character_spacing) is int
        assert line_spacing is None or type(line_spacing) is int
        assert label_spacing is None or type(label_spacing) is int
        assert minimum_distance is None or type(minimum_distance) is int

        assert text_dx is None or type(text_dx) is int
        assert text_dy is None or type(text_dy) is int

        self.name = safe_str(name)
        self.face_name = face_name
        self.fontset = safe_str(fontset)
        self.size = size or 10
        self.file = safe_str(file)
        self.type = safe_str(filetype)
        self.width = width
        self.height = height

        self.color = color
        self.character_spacing = character_spacing
        self.line_spacing = line_spacing
        self.label_spacing = label_spacing
        self.minimum_distance = minimum_distance
        self.text_dx = text_dx
        self.text_dy = text_dy

    def __repr__(self):
        return 'Shield(%s, %s, %s, %s)' % (self.name, ' '.join(self.face_name.values), self.size, self.file)

    def get_fontset_name(self):
        if len(self.face_name.values) > 1 and MAPNIK_VERSION < 200100:
            raise OutputException("Mapnik only supports multiple font face names as of version 2.1")

        if len(self.face_name.values) == 1:
            return None
        
        return fontset_name(self.face_name.values)
    
    def to_mapnik(self, fontsets=None):
        if MAPNIK_VERSION >= 200100:
            if self.get_fontset_name() is not None:
                sym = mapnik.ShieldSymbolizer(
                        mapnik.Expression('[%s]' % self.name), '', self.size or 10, 
                        mapnik.Color(str(self.color)) if self.color else mapnik.Color('black'), 
                        mapnik.PathExpression(self.file))

                sym.fontset = fontsets[self.get_fontset_name()]

            else:
                sym = mapnik.ShieldSymbolizer(
                        mapnik.Expression('[%s]' % self.name), self.face_name.values[0], self.size or 10, 
                        mapnik.Color(str(self.color)) if self.color else mapnik.Color('black'), 
                        mapnik.PathExpression(self.file))

        elif MAPNIK_VERSION >= 200000:
            sym = mapnik.ShieldSymbolizer(
                    mapnik.Expression('[%s]' % self.name), self.face_name.values[0], self.size or 10, 
                    mapnik.Color(str(self.color)) if self.color else mapnik.Color('black'), 
                    mapnik.PathExpression(self.file))
        else:
            sym = mapnik.ShieldSymbolizer(
                    self.name, self.face_name.values[0], self.size or 10, 
                    mapnik.Color(str(self.color)) if self.color else mapnik.Color('black'), 
                    self.file, self.type, self.width, self.height)

        sym.character_spacing = self.character_spacing or sym.character_spacing
        sym.line_spacing = self.line_spacing or sym.line_spacing
        sym.label_placement = self.label_spacing and mapnik.label_placement.LINE_PLACEMENT or sym.label_placement
        sym.label_spacing = self.label_spacing or sym.label_spacing
        sym.minimum_distance = self.minimum_distance or sym.minimum_distance

        if self.fontset:
            sym.fontset = self.fontset.value
        
        if MAPNIK_VERSION >= 200000:
            sym.displacement = (self.text_dx or 0, self.text_dy or 0)
        else:
            sym.displacement(self.text_dx or 0, self.text_dy or 0)
        
        return sym

class BasePointSymbolizer(object):
    def __init__(self, file, filetype, width, height):
        assert isinstance(file, basestring)
        assert isinstance(filetype, basestring)
        assert type(width) is int
        assert type(height) is int

        self.file = safe_str(file)
        self.type = safe_str(filetype)
        self.width = width
        self.height = height

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self.file)

    def to_mapnik(self):
        sym_class = getattr(mapnik, self.__class__.__name__)
        
        if MAPNIK_VERSION >= 200000:
            sym = sym_class(mapnik.PathExpression(self.file))
        else:
            sym = sym_class(self.file, self.type, self.width, self.height)
        
        return sym

class PointSymbolizer(BasePointSymbolizer):
    def __init__(self, file, filetype, width, height, allow_overlap=None):
        super(PointSymbolizer, self).__init__(file, filetype, width, height)

        assert allow_overlap is None or allow_overlap.__class__ is style.boolean

        self.allow_overlap = allow_overlap

    def to_mapnik(self):
        sym = super(PointSymbolizer, self).to_mapnik()
        
        sym.allow_overlap = self.allow_overlap.value if self.allow_overlap else sym.allow_overlap
        
        return sym
        

class PolygonPatternSymbolizer(BasePointSymbolizer):
    pass

class LinePatternSymbolizer(BasePointSymbolizer):
    pass
