#!/usr/bin/env python
# coding=utf-8
from __future__ import with_statement
import sys
import factory
from setuptools import setup, find_packages, Command
from os.path import join, dirname

class PyTest(Command):
    user_options = []
    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import sys,subprocess
        errno = subprocess.call(['py.test'])
        raise SystemExit(errno)

setup(
name='Factory',
version=factory.__version__,
author = factory.__author__,
author_email = factory.__email__,
description = factory.__description__,
license = factory.__license__,
keywords = factory.__keywords__,
url = factory.__url__,
long_description=open(join(dirname(__file__), 'README.md')).read(),
packages=find_packages(),
cmdclass = {'test': PyTest},
tests_require=['pytest', 'pytest_capturelog'],
install_requires=['gevent', 'argparse'],
entry_points={
'console_scripts': [
'fact = fabric.main:main',
]
},
classifiers=[
'Development Status :: 3 - Alpha',
'Environment :: Console',
'Intended Audience :: Developers',
'Intended Audience :: System Administrators',
'License :: OSI Approved :: MIT License',
'Operating System :: MacOS :: MacOS X',
'Operating System :: Unix',
'Operating System :: POSIX',
'Programming Language :: Python',
'Programming Language :: Python :: 2.5',
'Programming Language :: Python :: 2.6',
'Programming Language :: Python :: 2.7',
'Topic :: Software Development',
'Topic :: Software Development :: Build Tools',
'Topic :: Software Development :: Libraries',
'Topic :: Software Development :: Libraries :: Python Modules',
'Topic :: System :: Clustering',
'Topic :: System :: Software Distribution',
'Topic :: System :: Systems Administration',
],
)