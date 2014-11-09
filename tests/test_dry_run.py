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

import sys
import imp
import pytest
import factory
from test_factory_specification import hack

class TestAPI:
    def test_should_execute_dry_run_function(self, capsys):
        hack()
        sys.argv = ['factory.py', '--dry-run', "-r", "echo 'hello world!'"]
        factory.main.main()
        out, err = capsys.readouterr()
        print out
        assert "dry-in: echo 'hello world!'" in out
        assert "in: which echo; " in out 
        assert "out:" in out

    def test_should_execute_dry_sudo_function(self, capsys):
        hack()
        sys.argv = ['factory.py', '--dry-run', "-s", "echo 'hello world!'", "input=['\n', '\n', '\n']"]
        factory.main.main()
        out, err = capsys.readouterr()
        print out
        assert "dry-in: sudo -S echo 'hello world!'" in out
        assert "in: which sudo; which echo; " in out 
        assert "out:" in out

    def test_should_execute_dry_push_function(self, tmpdir, a, b, capsys):
        hack()
        sys.argv = ['factory.py', '--dry-run', "push", a, b]
        factory.main.main()
        out, err = capsys.readouterr()
        assert "dry-out: file '" in out
        assert "dry-out: path '" in out

    def test_should_execute_dry_pull_function(self, tmpdir, a, b, capsys):
        hack()
        sys.argv = ['factory.py', '--dry-run', "pull", a, b]
        factory.main.main()
        out, err = capsys.readouterr()
        assert "dry-out: file '" in out
        assert "dry-out: path '" in out

    def test_should_execute_dry_run_script_function(self, tmpdir, a, capsys):
        hack()
        sys.argv = ['factory.py', '--dry-run', "run_script", a]
        with open(a, 'w') as a:
            a.write('echo "hello world!"')
        factory.main.main()
        out, err = capsys.readouterr()
        assert "dry-out: file '" in out
        assert "dry-in: sh -s < " in out
        assert "in: which sh;" in out
        assert "out:" in out

    def test_should_execute_dry_open_shell_function(self, capsys):
        hack()
        sys.argv = ['factory.py', '--dry-run', "open_shell", 'hello, world!', "python -c 'print(raw_input())'"]
        factory.main.main()
        out, err = capsys.readouterr()
        assert "dry-in: python -c 'print(raw_input())" in out
        assert "in: which python; " in out
        assert "out:" in out

    def test_should_execute_factfile_without_fact(self, tmpdir, standalone_factfile, capsys):
        hack()
        standalone_factfile = imp.load_source('factfile', standalone_factfile)
        standalone_factfile.envs.common.dry_run = True
        standalone_factfile.main()
        out, err = capsys.readouterr()
        assert "dry-in: echo \"hello, world!\"" in out
        assert "in: which echo; " in out
        assert "out:" in out


class TestArgParsing:
    def test_should_set_dry_run(self, capsys):
        hack()
        sys.argv = ['factory.py', '--dry-run', "run", "echo 'hello world!'"]
        factory.main.main()
        try:
            assert factory.main.envs.common.dry_run == True
        finally:
            factory.main.envs.common.dry_run = False
