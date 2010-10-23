#!/usr/bin/env python

import os, sys
import math
import pprint
import urllib
import urlparse
import tempfile
import StringIO
import os.path
import zipfile
import itertools
import re
import ConfigParser
import codecs
import optparse

# Solves nasty problems:
# http://bytes.com/topic/python/answers/40109-missing-sys-setappdefaultencoding
reload(sys)
sys.setdefaultencoding('utf-8')

try:
    import lxml.etree as ElementTree
    from lxml.etree import Element, tostring
except ImportError:
    try:
        import xml.etree.ElementTree as ElementTree
        from xml.etree.ElementTree import Element, tostring
    except ImportError:
        import elementtree.ElementTree as ElementTree
        from elementtree.ElementTree import Element, tostring


standard_projections = {
    'srs900913' : '+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs',
    'srsMerc' :  '+proj=merc +lon_0=0 +k=1 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m +no_defs',
    'srs4326' : '+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs'
}

        
def add_source(sources, ds_name, params):
    if ds_name not in sources:
        sources[ds_name] = params
        return ds_name
    op = sources[ds_name]
    c = 0
    while True:
        for k,v in op.items():
            # dicts are unequal
            if k not in params or op[k] != params[k]:
                c += 1
                nds_name = "%s_%d" % (ds_name, c)
                if nds_name in sources:
                    op = sources[nds_name] 
                    break
                sources[nds_name] = params
                return nds_name
            else: # equal, return!
                return ds_name


#
class MyConfigParser(ConfigParser.RawConfigParser):
    def write(self, fp):
        """Write an .ini-format representation of the configuration state."""
        if self._defaults:
            fp.write("[%s]\n" % ConfigParser.DEFAULTSECT)
            for (key, value) in sorted(self._defaults.items(), key=lambda x: x[0]):
                fp.write("%s = %s\n" % (key, str(value).replace('\n', '\n\t')))
            fp.write("\n")
        for section in sorted(self._sections):
            fp.write("[%s]\n" % section)
            for (key, value) in sorted(self._sections[section].items(), key=lambda x: x[0]):
                if key != "__name__":
                    fp.write("%s = %s\n" %
                             (key, str(value).replace('\n', '\n\t')))
            fp.write("\n")


def convert(src, outmml, outconfig, opts):
    if os.path.exists(src): # local file
        # using 'file:' enables support on win32
        # for opening local files with urllib.urlopen
        # Note: this must only be used with abs paths to local files
        # otherwise urllib will think they are absolute, 
        # therefore in the future it will likely be
        # wiser to just open local files with open()
        if os.path.isabs(src) and sys.platform == "win32":
            src = 'file:%s' % src

    
    doc = ElementTree.parse(urllib.urlopen(src))
    map = doc.getroot()
    
    defaults = standard_projections
    sources = {}
    
    all_srs = dict([(v,k) for k,v in standard_projections.items()])
    
    name_filter = re.compile("\W")
    
    for layer in map.findall("Layer"):
        if not opts.extract_all and layer.attrib.get('status',"on").lower() == "off":
            map.remove(layer)
            continue
        srs = layer.attrib['srs']
        srs_name = all_srs.get(srs)
        if not srs_name:
            srs_name = "srs%d"%len(all_srs)
            defaults[srs_name] = srs
            all_srs[srs] = srs_name

        id = layer.attrib.get('id')
        classes = layer.attrib.get('class') 
        keys = []
        if id:
            keys.append("%s_" % id)
        if classes:
            keys.extend(classes.split(" "))
        ds_name = name_filter.sub("_", " ".join(keys))
        
        
        params = {}
        for param in layer.find("Datasource").findall("Parameter"):
            params[param.attrib['name']] = param.text
        
        params.update(layer.find("Datasource").attrib)
        params['layer_srs'] = "%%(%s)s" % srs_name
        
        ds_name = add_source(sources, ds_name, params)
        
        layer.attrib['source_name'] = ds_name
        del layer.attrib['srs']
        layer.remove(layer.find("Datasource"))

    # now generate unique bases
    g_params = {}
    
    for name, params in sources.items():
        gp = {}
        name_base = None
        if params.get('type') == 'postgis':
            param_set = ("port","host","user","layer_srs","password","type","dbname","estimate_extent","extent")
            name_base = "postgis_conn_%d"
#        elif params.get('type') == 'shape':
#            param_set = ("type","file","source_srs")
#            name_base = "shapefile_%d"
        else:
            continue

        for p in param_set:
            if p in params:
                gp[p] = params[p]
                del params[p]
                
        gp_name,gp_data = g_params.get(repr(gp),(None,None))        
        if not gp_name:
            gp_name = name_base % len(g_params)
            g_params[repr(gp)] = gp_name,gp
        
        params['template'] = gp_name
        
    config = MyConfigParser(defaults)     
    
    for name,params in itertools.chain(g_params.values(), sources.items()):
        config.add_section(name)
        for pn,pv in params.items():
            if pn == 'table': pv = pv.strip()
            config.set(name,pn,pv)
    with codecs.open(outconfig,"w","utf-8") as oc:
        config.write(oc)
    
    map.insert(0,Element("DataSourcesConfig", src=outconfig))
    doc.write(outmml, encoding="utf8")

    


        
if __name__ == "__main__":
    parser = optparse.OptionParser(usage= "usage: %s [options] <source.mml> <output.mml> <output.cfg>" % sys.argv[0])

    parser.add_option('-a', '--all', dest='extract_all', default=False, action="store_true",
                      help='Include disabled layers')

    (options, args) = parser.parse_args()
    if len(args) != 3:
        parser.error("Please specify <source.mml> <output.mml> <output.cfg>")
    
    inmml, outmml, outcfg = args
    convert(inmml, outmml, outcfg, options)

        
