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
import imp
import pytest
factory = imp.load_source(
    'factory',
    os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        '../factory.py'
        )
)


def test_should_write_command_stdout_to_sys_stdout(capsys):
    sys.argv = ['factory.py', "run:echo 'hello world!'"]
    factory.main()
    out, err = capsys.readouterr()
    assert "hello world!" in out


def test_should_write_command_stderr_to_sys_stderr(capsys):
    sys.argv = ['factory.py', 'run:qwertyuiop']
    factory.main()
    out, err = capsys.readouterr()
    assert "/bin/sh: 1: qwertyuiop: not found" in err
    

def test_should_parse_splited_arguments(capsys):
    sys.argv = ['factory.py', "run", "echo 'hello world!'"]
    factory.main()
    out, err = capsys.readouterr()
    assert "hello world!" in out


def test_should_execute_run_function(capsys):
    sys.argv = ['factory.py', "-r", "echo 'hello world!'"]
    factory.main()
    out, err = capsys.readouterr()
    assert "hello world!" in out


def test_should_execute_sudo_function(capsys):
    sys.argv = ['factory.py', "-s", "echo 'hello world!'"]
    factory.main()
    out, err = capsys.readouterr()
    assert "hello world!" in out


def test_should_execute_push_function(tmpdir, a, b, capsys):
    sys.argv = ['factory.py', "--push", a, b]
    factory.main()
    with open(a, 'r') as a, open(b, 'r') as b:
        assert a.read() == b.read()


def test_should_execute_pull_function(tmpdir, a, b, capsys):
    sys.argv = ['factory.py', "--pull", a, b]
    factory.main()
    with open(a, 'r') as a, open(b, 'r') as b:
        assert a.read() == b.read()


def test_should_execute_many_functions(capsys):
    sys.argv = ['factory.py', "run", "echo 'hello world!'", "run", "echo 'hello world!'"]
    factory.main()
    out, err = capsys.readouterr()
    assert "hello world!\nhello world!\n" in out


def test_should_communicate_with_stdin(capsys):
    sys.argv = ['factory.py', "sh"]
    sys.stdin.write("echo 'hello world!'; exit")
    sys.stdin.flush()
    factory.main()
    out, err = capsys.readouterr()
    assert "hello world!" in out


def test_should_write_logs():
    sys.argv = ['factory.py', "run", "echo 'hello world!'"]
    factory.main()
    with open('factory.log', 'r') as f:
        assert "hello world!" in f.readlines()[-1]


def test_should_only_write_logs(capsys):
    sys.argv = ['factory.py', "-n", "run", "echo 'hello world!'"]
    factory.main()
    out, err = capsys.readouterr()
    assert out == '' and err == ''
    with open('factory.log', 'r') as f:
        assert "hello world!" in f.readlines()[-1]


def test_should_parse_many_arguments(capsys):
    sys.argv = ['factory.py', "-nr", "echo 'hello world!'"]
    factory.main()
    out, err = capsys.readouterr()
    assert out == '' and err == ''
    with open('factory.log', 'r') as f:
        assert "hello world!" in f.readlines()[-1]


if __name__ == '__main__':
    pytest.main()
