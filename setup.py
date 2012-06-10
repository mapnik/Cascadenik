#!/usr/bin/env python
import sys

# setuptools allows magic downloading of dependencies
# but setuptools is often broken, so swallow the error if it's not there.

try:
    from setuptools import setup
    HAS_SETUPTOOLS = True
except ImportError:
    from distutils.core import setup
    HAS_SETUPTOOLS = False

from cascadenik import __version__ as VERSION

options = dict(name='cascadenik',
        version = VERSION,
        description='Cascading Stylesheets For Mapnik',
        author='Michal Migurski',
        author_email='mike@teczno.com',
        platforms='OS Independent',
        license='todo',
        requires=['Mapnik', 'cssutils'],
        keywords='Mapnik,xml,css,mapping',
        url='https://github.com/mapnik/Cascadenik',
        classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Utilities'
        ],
        zip_safe=False,
        scripts=['cascadenik-compile.py','cascadenik-style.py', 'cascadenik-extract-dscfg.py'],
        packages=['cascadenik'],
        )

try:
    options['long_description'] = file('README.md','rb').read()
except IOError:
    pass

if HAS_SETUPTOOLS:
    options.update({'install_requires':['cssutils>0.9.0']})

setup(**options)

if not HAS_SETUPTOOLS:
    warning = '\n***Warning*** Cascadenik also requires'
    missing = False
    try:
        import PIL
        # todo import Image ?
    except:
        try:
            import Image
        except:
            missing = True
            warning +=' PIL (easy_install PIL)'
    try:
        import cssutils
    except:
        missing = True
        warning +' cssutils (easy_install cssutils)'
    if missing:
        sys.stderr.write('%s\n' % warning)
