Cascadenik Changelog
====================

Version 2.6.3, November 17, 2012

 * Adjusted breakpoints in style.convertZoomTests() to follow mid-points of real scales.

Version 2.6.2, November 17, 2012

 * Fixed several broken unit tests by removing local dependency on data/test.shp.

Version 2.6.1, November 17, 2012

 * Fixed numerous Mapnik 2.1.0 deprecation warnings by version-checking in cascadenik.tests and cascadenik.output.

Version 2.6.0, November 17, 2012

 * Added `--style` option to cascadenik-compile.py for user-supplied local stylesheets.

Version 2.5.2, October 2, 2012

 * Changed expectations for multiple font names so that pre-2.1 versions of Mapnik no longer throw OutputException.

Version 2.5.1, September 26, 2012

 * Completed support for Mapnik FontSet to match correct XML serialization in Mapnik 2.1.1-pre.

Version 2.5.0, September 14, 2012

 * Added preliminary support for Mapnik FontSet.
   Multiple fonts can now be used in stylesheets with `text-face-name`
   and `shield-face-name` *but* XML serialization support is missing.
   See also https://github.com/mapnik/mapnik/issues/1483.

Version 2.4.3, June 16, 2012

 * Removed non-working PIL requirement from setup.py.
 * Slightly modified shapefile unzipping to be smarter about existing files.

Version 2.4.2, June 9, 2012

 * Fixed a rogue pass-by-value instead of deepcopy() in parse.parse_rule().

Version 2.4.1, June 1, 2012

 * Fixed a bad reference in cascadenik-compile.py.

Version 2.4.0, May 28, 2012

 * Added support for variables, based on Less CSS spec.

Version 2.3.0, May 28, 2012

 * Added support for nested rules, based on Less CSS spec.
 * Added support for lines without semicolons at block ends, per CSS spec.

Version 2.2.0, May 23, 2012

 * Added new `scale` argument to load_map(), compile() and `--2x` option to cascadenik-compile.py.

Version 2.1.1, May 22, 2012

 * Fixed longstanding bug with relative links from relative .mss stylesheet links.

Version 2.1.0, May 22, 2012

 * Added new `display: none` property and its opposite, `display: map`.

Version 2.0.2, May 3, 2012

 * Fixed a bug in setup.py that required README.md to be present when pip-installing.

Version 2.0.1, May 3, 2012

 * Fixed line-dasharray bug: https://github.com/mapnik/Cascadenik/issues/11.

Version 2.0.0, May 1, 2012

 * Updated for Mapnik 2.0.0.
 * Replaced `style.stylesheet_rulesets()`, `style.rulesets_declarations()`,
   with all-new `style.stylesheet_declarations()`.
 * Fixed support for negative numbers in attribute selectors.
 * Added Style `filter-mode="first"` to generated XML.
 * Switched away from a state machine approach to a generator approach inspired
   by Eli Bendersky: http://eli.thegreenplace.net/2009/08/29/co-routines-as-an-alternative-to-state-machines/.

Version 1.x.x
-------------

Version 1.1.2, December 3, 2011

 * Switched from `os.rename()` to `shutil.move()` in `cascadenik-compile.py`
   so cross-device moves would work.

Version 1.1.1, November 13, 2011
 
 * Fixed use of shield symbolizer displacement based on https://github.com/mapnik/mapnik/issues/947.

Version 1.1.0, November 13, 2011
 
 * Added `shield-text-dx` and `shield-text-dy` properties.

Version 1.0.2, November 27, 2010
 
 * Fixed `is_gym`/`is_merc` bug from https://github.com/mapnik/Cascadenik/issues/closed#issue/10.

Version 1.0.1, November 27, 2010
 
 * Updated the CHANGELOG.
 * Modified packaging script from `deploy.py` to Makefile.

Version 1.0.0, October 4, 2010
 
 * Removed numerous command-line flags from `cascadenik-compile.py`; see `--help` for info.
 * Substantially modified path usage to be internally consistent for local and remote paths.
 * Added new `.ini`-based datasource configuration (Nino Walker).
 * Switched from python-based XML output to Mapnik-based XML output (Robert Coup).
 * Added new use of `~/.cascadenik` directory for locally-cached files.
 * Made local cache aware of HTTP 304 to minimize network traffic.
 * Started to write CHANGELOG for 1.0.0 but it's late.

Version 0.x.x
-------------

Version 0.2.0, August ?, 2010
 
 * Packaged from r?.
 * Added support for handling remote, single file-based datasources other than zipped shapefiles.
 * Added support for MarkersSymbolizer, RasterSymbolizer, and MetaWriters:
     - http://trac.mapnik.org/wiki/MarkersSymbolizer
     - http://trac.mapnik.org/wiki/MetaWriter
     - http://trac.mapnik.org/wiki/RasterSymbolizer
 * Added support for zipped shapefiles that are local to the filesystem.
 * Re-implemented support for installing dependencies via Setuptools, if available.
 * Refactored handling of file-based resources.
 * Added preliminary support for writing XML compliant against different Mapnik versions.
 * Added support for caching (avoiding re-downloading) remote resources (initial patch from tmcw)
 * Exposed the variety of new options as command line flags for `cascadenik-compile.py`.
 
Version 0.1.0, May 1, 2010

 * Initial release.
 * Packaged from r941
