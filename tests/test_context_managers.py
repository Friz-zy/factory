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

def test_with_set_connect_env():
    from factory.api import *
    from factory.context_managers import set_connect_env

    assert connect_env.__dict__ == {}
    with set_connect_env('localhost'):
        assert connect_env.host == 'localhost'
        with set_connect_env('127.0.0.1'):
            assert connect_env.host == '127.0.0.1'
        assert connect_env.host == 'localhost'
    assert connect_env.__dict__ == {}

