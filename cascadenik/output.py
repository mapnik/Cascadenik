import style

try:
    import mapnik
except ImportError:
    # *.to_mapnik() won't work, maybe that's okay?
    pass

class Map:
    def __init__(self, srs=None, layers=None, bgcolor=None):
        assert srs is None or type(srs) is str
        assert layers is None or type(layers) in (list, tuple)
        assert bgcolor is None or bgcolor.__class__ is style.color or bgcolor == 'transparent'
        
        self.srs = srs
        self.layers = layers or []
        self.bgcolor = bgcolor

    def __repr__(self):
        return 'Map(%s %s)' % (self.bgcolor, repr(self.layers))

    def to_mapnik(self, mmap):
        """
        """
        mmap.srs = self.srs or mmap.srs
        mmap.bgcolor = str(self.bgcolor) or mmap.bgcolor
        
        ids = (i for i in xrange(1, 999999))
        
        for layer in self.layers:
            for style in layer.styles:

                sty = mapnik.Style()
                
                for rule in style.rules:
                    rul = mapnik.Rule('rule %d' % ids.next())
                    rul.filter = rule.filter and mapnik.Filter(rule.filter.text) or rul.filter
                    rul.min_scale = rule.minscale and rule.minscale.value or rul.min_scale
                    rul.max_scale = rule.maxscale and rule.maxscale.value or rul.max_scale
                    
                    for symbolizer in rule.symbolizers:
                        if not hasattr(symbolizer, 'to_mapnik'):
                            continue

                        sym = symbolizer.to_mapnik()
                        rul.symbols.append(sym)
                    sty.rules.append(rul)
                mmap.append_style(style.name, sty)

            lay = mapnik.Layer(layer.name)
            lay.srs = layer.srs or lay.srs
            lay.minzoom = layer.minzoom or lay.minzoom
            lay.maxzoom = layer.maxzoom or lay.maxzoom
            
            for style in layer.styles:
                lay.styles.append(style.name)

            mmap.layers.append(lay)
                    
                    
        

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
        assert type(name) is str
        assert styles is None or type(styles) in (list, tuple)
        assert srs is None or type(srs) is str
        assert minzoom is None or type(minzoom) in (int, float)
        assert maxzoom is None or type(maxzoom) in (int, float)
        
        self.name = name
        self.datasource = datasource
        self.styles = styles or []
        self.srs = srs
        self.minzoom = minzoom
        self.maxzoom = maxzoom

    def __repr__(self):
        return 'Layer(%s: %s)' % (self.name, repr(self.styles))

class Datasource:
    def __init__(self, **parameters):
        self.parameters = parameters

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
        assert mode is None or type(mode) is str
        assert scaling is None or type(scaling) is str

        self.mode = mode
        self.opacity = opacity or 1.0
        self.scaling = scaling

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
        assert join is None or type(join) is str
        assert cap is None or type(cap) is str
        assert dashes is None or dashes.__class__ is style.numbers

        self.color = color
        self.width = width
        self.opacity = opacity
        self.join = join
        self.cap = cap
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
            stroke.add_dash(*self.dashes.values)
        sym = mapnik.LineSymbolizer(stroke)
        
        return sym

class TextSymbolizer:
    def __init__(self, name, face_name, size, color, wrap_width=None, \
        spacing=None, label_position_tolerance=None, max_char_angle_delta=None, \
        halo_color=None, halo_radius=None, dx=None, dy=None, avoid_edges=None, \
        min_distance=None, allow_overlap=None, placement=None, \
        character_spacing=None, line_spacing=None, text_transform=None, fontset=None):

        assert type(name) is str
        assert face_name is None or type(face_name) is str
        assert fontset is None or type(fontset) is str
        assert type(size) is int
        assert color.__class__ is style.color
        assert wrap_width is None or type(wrap_width) is int
        assert spacing is None or type(spacing) is int
        assert label_position_tolerance is None or type(label_position_tolerance) is int
        assert max_char_angle_delta is None or type(max_char_angle_delta) is int
        assert halo_color is None or halo_color.__class__ is style.color
        assert halo_radius is None or type(halo_radius) is int
        assert dx is None or type(dx) is int
        assert dy is None or type(dy) is int
        assert character_spacing is None or type(character_spacing) is int
        assert line_spacing is None or type(line_spacing) is int
        assert avoid_edges is None or avoid_edges.__class__ is style.boolean
        assert min_distance is None or type(min_distance) is int
        assert allow_overlap is None or allow_overlap.__class__ is style.boolean
        assert placement is None or type(placement) is str
        assert text_transform is None or type(text_transform) is str

        assert face_name or fontset, "Must specify either face_name or fontset"

        self.name = name
        self.face_name = face_name or ''
        self.fontset = fontset
        self.size = size
        self.color = color

        self.wrap_width = wrap_width
        self.spacing = spacing
        self.label_position_tolerance = label_position_tolerance
        self.max_char_angle_delta = max_char_angle_delta
        self.halo_color = halo_color
        self.halo_radius = halo_radius
        self.dx = dx
        self.dy = dy
        self.character_spacing = character_spacing
        self.line_spacing = line_spacing
        self.avoid_edges = avoid_edges
        self.min_distance = min_distance
        self.allow_overlap = allow_overlap
        self.placement = placement
        self.text_transform = text_transform

    def __repr__(self):
        return 'Text(%s, %s)' % (self.face_name, self.size)

    def to_mapnik(self):
        sym = mapnik.TextSymbolizer(self.name, self.face_name, self.size,
                                    mapnik.Color(str(self.color)))

        sym.wrap_width = self.wrap_width or sym.wrap_width
        sym.label_spacing = self.spacing or sym.label_spacing
        sym.label_position_tolerance = self.label_position_tolerance or sym.label_position_tolerance
        sym.max_char_angle_delta = self.max_char_angle_delta or sym.max_char_angle_delta
        sym.halo_fill = mapnik.Color(str(self.halo_color)) if self.halo_color else sym.halo_fill
        sym.halo_radius = self.halo_radius or sym.halo_radius
        sym.character_spacing = self.character_spacing or sym.character_spacing
        sym.line_spacing = self.line_spacing or sym.line_spacing
        sym.avoid_edges = self.avoid_edges.value if self.avoid_edges else sym.avoid_edges
        sym.minimum_distance = self.min_distance or sym.minimum_distance
        sym.allow_overlap = self.allow_overlap.value if self.allow_overlap else sym.allow_overlap
        if self.fontset:
            sym.fontset = self.fontset.value
        
        sym.displacement(self.dx or 0, self.dy or 0)
        
        return sym

class ShieldSymbolizer:
    def __init__(self, name, face_name=None, size=None, file=None, filetype=None, \
        width=None, height=None, color=None, min_distance=None, character_spacing=None, \
        line_spacing=None, spacing=None, fontset=None):
        
        assert ((face_name or fontset) and size) or file
        
        assert type(name) is str
        assert face_name is None or type(face_name) is str
        assert fontset is None or type(fontset) is str
        assert size is None or type(size) is int
        assert width is None or type(width) is int
        assert height is None or type(height) is int

        assert color is None or color.__class__ is style.color
        assert character_spacing is None or type(character_spacing) is int
        assert line_spacing is None or type(line_spacing) is int
        assert spacing is None or type(spacing) is int
        assert min_distance is None or type(min_distance) is int

        self.name = name
        self.face_name = face_name or ''
        self.fontset = fontset
        self.size = size
        self.file = file
        self.type = filetype
        self.width = width
        self.height = height

        self.color = color
        self.character_spacing = character_spacing
        self.line_spacing = line_spacing
        self.spacing = spacing
        self.min_distance = min_distance

    def __repr__(self):
        return 'Shield(%s, %s, %s, %s)' % (self.name, self.face_name, self.size, self.file)

    def to_mapnik(self):
        sym = mapnik.ShieldSymbolizer(
                self.name, 
                self.face_name, 
                self.size, 
                mapnik.Color(str(self.color)) if self.color else None, 
                self.file, 
                self.type, 
                self.width, 
                self.height)
        
        sym.character_spacing = self.character_spacing or sym.character_spacing
        sym.line_spacing = self.line_spacing or sym.line_spacing
        sym.spacing = self.spacing or sym.line_spacing
        sym.minimum_distance = self.min_distance or sym.minimum_distance
        if self.fontset:
            sym.fontset = self.fontset.value
        
        return sym

class BasePointSymbolizer(object):
    def __init__(self, file, filetype, width, height):
        assert type(file) is str
        assert type(filetype) is str
        assert type(width) is int
        assert type(height) is int

        self.file = file
        self.type = filetype
        self.width = width
        self.height = height

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self.file)

    def to_mapnik(self):
        sym_class = getattr(mapnik, self.__class__.__name__)
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
