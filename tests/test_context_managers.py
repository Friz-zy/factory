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
from factory.api import *

def test_with_set_connect_env():
    assert envs.connect.__dict__ == {}
    with set_connect_env('localhost'):
        assert envs.connect.host == 'localhost'
        with set_connect_env('127.0.0.1'):
            assert envs.connect.host == '127.0.0.1'
        assert envs.connect.host == 'localhost'
    assert envs.connect.__dict__ == {}


def test_with_set_global_env():
    original = envs.common.__dict__
    with set_global_env('test'):
        assert envs.common.test == True
        with set_global_env(test=False):
            assert envs.common.test == False
        assert envs.common.test == True
    assert envs.common.__dict__ == original

# TODO: check isolation from another global_dict modification: maybe should running task into process