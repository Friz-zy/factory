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

    def test_should_execute_run_script_function(self, tmpdir, a, capsys):
        sys.argv = ['factory.py', "run_script", a]
        with open(a, 'w') as a:
            a.write('echo "hello world!"')
        factory.main()
        out, err = capsys.readouterr()
        print out, err
        assert "hello world!" in out

    def test_should_execute_run_function_with_input(self, capsys):
        sys.argv = ['factory.py', "-r", "python -c 'print(raw_input())'", "input='hello, world!'"]
        factory.main()
        out, err = capsys.readouterr()
        assert "hello, world!" in out

    def test_should_execute_open_shell_function(self, capsys):
        sys.argv = ['factory.py', "open_shell", 'hello, world!', "python -c 'print(raw_input())'"]
        factory.main()
        out, err = capsys.readouterr()
        assert "hello, world!" in out


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
        assert out.count('hello world!') == 4

    def test_should_parse_many_arguments(self, capsys):
        sys.argv = ['factory.py', "-nr", "echo 'hello world!'"]
        factory.main()
        out, err = capsys.readouterr()
        assert out == '' and err == ''
        with open('factory.log', 'r') as f:
            assert "hello world!" in f.readlines()[-1]

    def test_should_parallel_executing(self, capsys):
        sys.argv = ['factory.py', '-p', "run", "sleep 1; echo -n 'world!'", "run", "echo -n 'hello'"]
        factory.main()
        out, err = capsys.readouterr()
        print out
        assert out.rfind('hello') < out.rfind('world!')


class TestFeedback:
    def test_should_write_command_stdout_to_sys_stdout(self, capsys):
        sys.argv = ['factory.py', "run:echo 'hello world!'"]
        factory.main()
        out, err = capsys.readouterr()
        assert "hello world!" in out

    def test_should_write_command_stderr_to_sys_stdout(self, capsys):
        sys.argv = ['factory.py', 'run:qwertyuiop']
        factory.main()
        out, err = capsys.readouterr()
        assert "/bin/sh: 1: qwertyuiop: not found" in out

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
        with open('factory.log', 'r') as f:
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

    def test_should_write_command_stderr_to_sys_stdout(self, capsys):
        sys.argv = ['factory.py', 'run:qwertyuiop,err_to_out=True']
        factory.main()
        out, err = capsys.readouterr()
        assert "/bin/sh: 1: qwertyuiop: not found" in out

    def test_should_load_config(self, tmpdir, config, capsys):
        sys.argv = ['factory.py', '--config', config, "run:echo 'hello world!'"]
        factory.main()
        out, err = capsys.readouterr()
        assert "hello world!" in out


if __name__ == '__main__':
    pytest.main()
