#!/usr/bin/env python
# -*- coding: utf-8 -*- 
"""Requirements specification for the factory"""
from __future__ import with_statement

__author__ = 'Filipp Frizzy'
__credits__ = ["Filipp Frizzy"]
__license__ = "MIT"
__version__ = ""
__maintainer__ = "Filipp Frizzy"
__email__ = "filipp.s.frizzy@gmail.com"
__status__ = "Development"

import os
import sys
import json
import pytest
import subprocess


path_to_factory = os.path.abspath(os.path.join(
                   os.path.dirname(os.path.realpath(__file__)),
                   '..'))
sys.path.append(path_to_factory)


@pytest.fixture()
def a(tmpdir):
    a = str(tmpdir.join('a'))
    with open(a, 'w') as f:
        f.write('hello, world!')
    return a


@pytest.fixture()
def b(tmpdir):
    return str(tmpdir.join('b'))


@pytest.fixture()
def config(tmpdir):
    config = tmpdir.join('factory.json')
    with open(str(config), 'w') as f:
        f.write(json.dumps({'split_function': '::'}))
    return str(config)


@pytest.fixture()
def factfile(tmpdir):
    file = tmpdir.join('factfile.py')
    with open(str(file), 'w') as f:
        f.write(
"""from factory.api import run

def hello():
    run('echo "hello, world!"')
"""
    )
    return str(file)


@pytest.fixture()
def fabfile(tmpdir):
    file = tmpdir.join('fabfile.py')
    with open(str(file), 'w') as f:
        f.write(
"""from fabric.api import run

def hello():
    run('echo "hello, world!"')
"""
    )
    return str(file)
