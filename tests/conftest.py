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


import pytest

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
        f.write("{'split_function': ';'}\n")
    return str(config)
