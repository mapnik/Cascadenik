#!/usr/bin/env python

# Learned it all here: http://ianbicking.org/docs/setuptools-presentation/
# and here: http://peak.telecommunity.com/DevCenter/setuptools

try:
    from setuptools import setup, find_packages
except:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

readme = file('README.txt','rb').read()

setup(name='cascadenik',
        version = '0.1.0',
        description='Cascading Stylesheets For Mapnik',
        long_description=readme,
        author='Michal Migurski',
        author_email='mike@teczno.com',
        platforms='OS Independent',
        license='todo',
        requires=['Mapnik','cssutils'],
        install_requires = 'cssutils>0.9.0',
        test_suite = 'tests.test',
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
        #scripts=['cascadenik/compile.py','cascadenik/style.py'],
        # grab the script that just call main...
        scripts=['compile.py','style.py'],
        packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
        zip_safe=False, # not sure what this does...
        )