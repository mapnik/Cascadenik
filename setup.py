#!/usr/bin/env python

try:
    from setuptools import setup, find_packages
except:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

readme = file('README.txt','rb').read()

setup(name='cascadenik',
        version = '0.1.0',
        #py_modules = ['../cascadenik'],
        description='Cascading Stylesheets For Mapnik',
        long_description=readme,
        author='Michal Migurski',
        author_email='mike@teczno.com',
        platforms='OS Independent',
        license='todo',
        requires=['Mapnik','cssutils'],
        #test_suite = 'tests.run_doc_tests',
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
        #scripts = ['nik2img.py'],
        #packages=['niktests'],
        packages=find_packages(exclude=[]),
        zip_safe=False,
        )