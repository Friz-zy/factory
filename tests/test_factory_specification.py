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
import StringIO
import pytest
factory = imp.load_source(
    'factory',
    os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        '../factory.py'
        )
)


class TestAPI:
    def test_should_execute_run_function(self, capsys):
        sys.argv = ['factory.py', "-r", "echo 'hello world!'"]
        factory.main()
        out, err = capsys.readouterr()
        assert "hello world!" in out

    def test_should_execute_sudo_function(self, capsys):
        sys.argv = ['factory.py', "-s", "echo 'hello world!'"]
        factory.main()
        out, err = capsys.readouterr()
        assert "hello world!" in out

    def test_should_execute_push_function(self, tmpdir, a, b, capsys):
        sys.argv = ['factory.py', "push", a, b]
        factory.main()
        with open(a, 'r') as a, open(b, 'r') as b:
            assert a.read() == b.read()


    def test_should_execute_pull_function(self, tmpdir, a, b, capsys):
        sys.argv = ['factory.py', "pull", a, b]
        factory.main()
        with open(a, 'r') as a, open(b, 'r') as b:
            assert a.read() == b.read()


class TestArgParsing:
    def test_should_parse_splited_arguments(self, capsys):
        sys.argv = ['factory.py', "run", "echo 'hello world!'"]
        factory.main()
        out, err = capsys.readouterr()
        assert "hello world!" in out

    def test_should_execute_many_functions(self, capsys):
        sys.argv = ['factory.py', "run", "echo 'hello world!'", "run", "echo 'hello world!'"]
        factory.main()
        out, err = capsys.readouterr()
        assert out.count('hello world!') == 2

    def test_should_parse_many_arguments(self, capsys):
        sys.argv = ['factory.py', "-nr", "echo 'hello world!'"]
        factory.main()
        out, err = capsys.readouterr()
        assert out == '' and err == ''
        with open('factory.log', 'r') as f:
            assert "hello world!" in f.readlines()[-1]

    def test_should_parallel_executing(self, capsys):
        sys.argv = ['factory.py', '-p', "run", "sleep 1; echo 'world!'", "run", "echo 'hello'"]
        factory.main()
        out, err = capsys.readouterr()
        assert out.find('hello') < out.find('world!')


class TestFeedback:
    def test_should_write_command_stdout_to_sys_stdout(self, capsys):
        sys.argv = ['factory.py', "run:echo 'hello world!'"]
        factory.main()
        out, err = capsys.readouterr()
        assert "hello world!" in out


    def test_should_write_command_stderr_to_sys_stderr(self, capsys):
        sys.argv = ['factory.py', 'run:qwertyuiop']
        factory.main()
        out, err = capsys.readouterr()
        assert "/bin/sh: 1: qwertyuiop: not found" in err


    def test_should_communicate_with_stdin(self, capsys):
        sys.argv = ['factory.py', "sh"]
        #oin = sys.stdin
        #sys.stdin = StringIO.StringIO("echo 'hello world!'; exit")
        #factory.main()
        #sys.stdin = oin
        out, err = capsys.readouterr()
        assert "hello world!" in out


    def test_should_write_logs(self):
        sys.argv = ['factory.py', "run", "echo 'hello world!'"]
        factory.main()
        with open('factory.logc', 'r') as f:
            assert "hello world!" in f.readlines()[-2]


    def test_should_only_write_logs(self, capsys):
        sys.argv = ['factory.py', "-n", "run", "echo 'hello world!'"]
        factory.main()
        out, err = capsys.readouterr()
        assert out == '' and err == ''
        with open('factory.logc', 'r') as f:
            assert "hello world!" in f.readlines()[-2]


    def test_should_work_with_unicode(self, capsys):
        sys.argv = ['factory.py', "run:echo 'привет, мир!'"]
        factory.main()
        out, err = capsys.readouterr()
        print out, err
        assert "привет, мир!" in out
        assert err == ''


if __name__ == '__main__':
    pytest.main()
