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
        # Note: easy_install with PIL is bizarre. It requires adding
        # the dependency link and the 'Imaging' keyword and on mac os
        # to get the import PIL working requires manually add a file 
        # called 'PIL.pth' with the word PIL in it to your site-packages.
        # ie get your site packaged dir
        # $ python -c 'from distutils.sysconfig import get_python_lib; print get_python_lib()'
        # Then place the PIL.pth file
        # sudo echo 'PIL' > /path/to/site-packages/PIL.pth
        install_requires = ['cssutils>0.9.0','Imaging'],
        dependency_links = ['http://effbot.org/downloads/#Imaging'],
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
        scripts=['cascadenik-compile.py','cascadenik-style.py'],
        packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
        zip_safe=False, # not sure what this does...
        )
