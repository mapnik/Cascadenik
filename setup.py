#!/usr/bin/env python

from distutils.core import setup

readme = file('README.txt','rb').read()

setup(name='cascadenik',
        version = '0.1.0',
        description='Cascading Stylesheets For Mapnik',
        long_description=readme,
        author='Michal Migurski',
        author_email='mike@teczno.com',
        platforms='OS Independent',
        license='todo',
        requires=['Mapnik','cssutils','PIL'],
        keywords='Mapnik,xml,css,mapping',
        url='http://mapnik-utils.googlecode.com/',
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
        scripts=['cascadenik-compile.py','cascadenik-style.py'],
        packages=['cascadenik'],
        )
