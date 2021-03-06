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
from test_factory_specification import hack

def test_with_set_connect_env():
    hack()
    assert envs.connect.__dict__ == {}
    with set_connect_env('localhost'):
        assert envs.connect.host == 'localhost'
        with set_connect_env('127.0.0.1'):
            assert envs.connect.host == '127.0.0.1'
        assert envs.connect.host == 'localhost'
    assert envs.connect.__dict__ == {}


def test_with_set_common_env():
    hack()
    original = envs.common.__dict__
    with set_common_env('test'):
        assert envs.common.test == True
        with set_common_env(test=False):
            assert envs.common.test == False
        assert envs.common.test == True
    assert envs.common.__dict__ == original

# TODO: check isolation from another common_dict modification: maybe should running task into process


def test_with_hide():
    hack()
    with set_common_env('interactive', 'show_errors'):
        original = envs.common.__dict__
        # hide out only
        with hide('stdout'):
            assert envs.common.interactive == False
            assert envs.common.show_errors == True
        # hide err only
        with hide('stderr'):
            assert envs.common.show_errors == False
            assert envs.common.interactive == True
        # hide out and err
        with hide('stdout', 'stderr'):
            assert envs.common.interactive == False
            assert envs.common.show_errors == False
        with hide():
            assert envs.common.interactive == False
            assert envs.common.show_errors == False
        assert original == envs.common.__dict__


def test_with_show():
    hack()
    with set_common_env(interactive=False, show_errors=False):
        original = envs.common.__dict__
        # show out only
        with show('stdout'):
            assert envs.common.interactive == True
            assert envs.common.show_errors == False
        # show err only
        with show('stderr'):
            assert envs.common.show_errors == True
            assert envs.common.interactive == False
        # show out and err
        with show('stdout', 'stderr'):
            assert envs.common.interactive == True
            assert envs.common.show_errors == True
        with show():
            assert envs.common.interactive == True
            assert envs.common.show_errors == True
        assert original == envs.common.__dict__


def test_with_settings():
    hack()
    original = envs.common.__dict__
    with settings(hide('stdout'), show('stderr'), 'test', test1=False):
        print envs.common
        assert envs.common.interactive == False
        assert envs.common.show_errors == True
        assert envs.common.test == True
        assert envs.common.test1 == False
    assert envs.common.__dict__ == original


def test_issue_1(capsys):
    """Test for https://github.com/Friz-zy/factory/issues/1"""
    hack()
    with set_connect_env('localhost'):
        run('echo 000')
        out, err = capsys.readouterr()
        assert out.count('in: echo 000') == 1
        assert out.count('out: 000') == 1
        with set_connect_env('127.0.0.1'):
            out = run('echo 111')
            out, err = capsys.readouterr()
            assert out.count('in: echo 111') == 1
            assert out.count('out: 111') == 1
            with set_connect_env('localhost'):
                out = run('echo 222')
                out, err = capsys.readouterr()
                assert out.count('in: echo 222') == 1
                assert out.count('out: 222') == 1
