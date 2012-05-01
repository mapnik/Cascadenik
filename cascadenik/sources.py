import ConfigParser
import StringIO
import urlparse
import urllib

from . import mapnik

class DataSources(object):
    def __init__(self, base, local_cfg):
        self.templates = set([])
        self.sources = {}
        self.defaults = {}
        self.local_cfg_data = None
        self.local_cfg_url = None
        self.finalized = False
        
        # avoid circular import
        import compile
        self.msg = compile.msg     
        
        # if a local_cfg is provided, we want to get the defaults first, before reading any other
        # configuration.
        if local_cfg:
            self.local_cfg_url = urlparse.urljoin(base, local_cfg)
            self.msg("Using local datasource config: %s" % self.local_cfg_url)
            self.set_local_cfg_data(urllib.urlopen(self.local_cfg_url).read().decode(compile.DEFAULT_ENCODING))
            
    def set_local_cfg_data(self, data):
        self.local_cfg_data = data
        locals = OverrideConfigParser({})
        locals.loads(data)
        self.defaults = locals.defaults()

    def finalize(self):
        if self.local_cfg_data:
            self.msg("Loading local config data: %s" % self.local_cfg_url)
            self.add_config(self.local_cfg_data, self.local_cfg_url)
        self.finalized = True

    def get(self, name):
        if not self.finalized:
            self.finalize()
        return self.sources.get(name)

    def add_config(self, textdata, filename):
        parser = OverrideConfigParser(self.defaults)
        parser.loads(textdata)

        for sect in parser.sections():
            options = {}
            name = sect
            dtype = parser.get(sect,"type") if parser.has_option(sect, "type") else None
            template = parser.get(sect,"template") if parser.has_option(sect, "template") else None
            layer_srs = parser.get(sect,"layer_srs") if parser.has_option(sect, "layer_srs") else None

            # this layer declares a template template
            if template:
                self.templates.add(template)
                # the template may have been declared already, or we haven't processed it yet.
                if template in self.sources:
                    dtype = self.sources[template]['parameters'].get('type', dtype)
                    layer_srs = self.sources[template].get('layer_srs', layer_srs)
                else:
                    # TODO catch section missing errors
                    dtype = parser.get(template, 'type')
                    layer_srs = parser.get(template, 'layer_srs') if parser.has_option(template, 'layer_srs') else layer_srs

            # handle the most common projections
            if layer_srs and layer_srs.lower().startswith("epsg:"):
                if self.PROJ4_PROJECTIONS.get(layer_srs.lower()):
                    layer_srs = self.PROJ4_PROJECTIONS.get(layer_srs.lower())
                else:
                    layer_srs = '+init=%s' % layer_srs

            # try to init the projection
            if layer_srs:
                try:
                    mapnik.Projection(str(layer_srs))
                except Exception, e:
                    raise Exception("Section [%s] declares an invalid layer_srs (%s) in %s.\n\t%s" % (sect, layer_srs, filename, e))
                    
            if dtype:
                options['type'] = dtype
            else:
                raise Exception("Section [%s] missing 'type' information in %s." % (sect, filename))
            
            # now populate the options for this type of source, looping over all the valid params
            for option, option_type in self.XML_OPTIONS[dtype].items():
                opt_value = None
                try:
                    if option_type == int:
                        opt_value = parser.getint(sect,option)
                    elif option_type == float:
                        opt_value = parser.getfloat(sect,option)
                    elif option_type == bool:
                        opt_value = parser.getboolean(sect,option)
                    else:
                        opt_value = parser.get(sect,option)
                except ConfigParser.NoOptionError:
                    pass
                except ValueError, e:
                    raise ValueError("Section [%s], field '%s' in file %s contains an invalid value: %s" % (sect, option, filename, e))

                if opt_value is not None:
                    options[option] = opt_value

            # build an object mirroring the XML Datasource object
            conf = dict(parameters=options)
            if template:
                conf['template'] = template
            if layer_srs:
                conf['layer_srs'] = layer_srs
            self.sources[name] = conf
                

    PROJ4_PROJECTIONS = {"epsg:4326" : "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs",
                         "epsg:900913" : "+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext  +no_defs"
                         }

    XML_OPTIONS = {"shape" : dict(file=str,encoding=str,base=str),
                   "postgis" : dict(cursor_size=int,
                                    dbname=str,
                                    geometry_field=str,
                                    estimate_extent=bool,
                                    host=str,
                                    initial_size=int,
                                    max_size=int,
                                    multiple_geometries=bool,
                                    password=str,
                                    persist_connection=bool,
                                    port=int,
                                    row_limit=int,
                                    table=str,
                                    srid=int,
                                    user=str),
                   "ogr" : dict(layer=str, file=str),
                   "osm" : dict(file=str, parser=str, url=str, bbox=str),
                   "gdal": dict(file=str, base=str),
                   "occi": dict(user=str, password=str, host=str, table=str,
                                initial_size=int,
                                max_size=int,
                                estimate_extent=bool,
                                encoding=str,
                                geometry_field=str,
                                use_spatial_index=bool,
                                multiple_geometries=bool),
                   "sqlite":dict(file=str,
                                 table=str,
                                 base=str,
                                 encoding=str,
                                 metadata=str,
                                 geometry_field=str,
                                 key_field=str,
                                 row_offset=int,
                                 row_limit=int,
                                 wkb_format=str,
                                 multiple_geometries=bool,
                                 use_spatial_index=bool),
                   "kismet":dict(host=str,
                                 port=int,
                                 encoding=str),
                   "raster":dict(file=str,
                                 lox=float,
                                 loy=float,
                                 hix=float,
                                 hiy=float,
                                 base=str),
                   }

    # add in global options
    for v in XML_OPTIONS.values():
        v.update(dict(type=str, estimate_extent=bool, extent=str))

class OverrideConfigParser(ConfigParser.SafeConfigParser):
    def __init__(self, overrides):
        ConfigParser.SafeConfigParser.__init__(self, overrides)
        self.overrides = overrides

    def loads(self, textdata):
        data = StringIO.StringIO(textdata)
        data.seek(0)
        self.readfp(data)

    def get(self, section, option):
        return ConfigParser.SafeConfigParser.get(self, section, option, vars=self.overrides)
    
