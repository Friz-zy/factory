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
from copy import copy
import pytest
import time
import factory

def hack():
    factory.main.logging.root.manager.loggerDict = {}
    factory.context_managers.connects = {}
    factory.main.envs.common.dry_run = False

class TestAPI:
    def test_should_import_api(self):
        try:
            from factory.api import *
            from factory import main as fact
        except ImportError as e:
            raise e

    def test_should_execute_run_function(self, capsys):
        hack()
        sys.argv = ['factory.py', "-r", "echo 'hello world!'"]
        factory.main.main()
        out, err = capsys.readouterr()
        assert "hello world!" in out

    def test_should_execute_sudo_function(self, capsys):
        hack()
        sys.argv = ['factory.py', "-s", "echo 'hello world!'", "input=['\n', '\n', '\n']"]
        factory.main.main()
        out, err = capsys.readouterr()
        assert "sudo -S echo 'hello world!'" in out
        assert "out: hello world!" in out or "err: sudo: 3 " in out

    def test_should_execute_push_function(self, tmpdir, a, b, capsys):
        hack()
        sys.argv = ['factory.py', "push", a, b]
        factory.main.main()
        with open(a, 'r') as a:
            with open(b, 'r') as b:
                assert a.read() == b.read() == 'hello, world!'

    def test_should_execute_pull_function(self, tmpdir, a, b, capsys):
        hack()
        sys.argv = ['factory.py', "pull", a, b]
        factory.main.main()
        with open(a, 'r') as a:
            with open(b, 'r') as b:
                assert a.read() == b.read() == 'hello, world!'

    def test_should_execute_run_script_function(self, tmpdir, a, capsys):
        hack()
        sys.argv = ['factory.py', "run_script", a]
        with open(a, 'w') as a:
            a.write('echo "hello world!"')
        factory.main.main()
        out, err = capsys.readouterr()
        assert "hello world!" in out

    def test_should_execute_run_function_with_input(self, capsys):
        hack()
        sys.argv = ['factory.py', "-r", "python -c 'print(raw_input())'", "input='hello, world!'"]
        factory.main.main()
        out, err = capsys.readouterr()
        assert "hello, world!" in out

    def test_should_execute_open_shell_function(self, capsys):
        hack()
        sys.argv = ['factory.py', "open_shell", 'hello, world!', "python -c 'print(raw_input())'"]
        factory.main.main()
        out, err = capsys.readouterr()
        assert "hello, world!" in out

    def test_should_execute_factfile_without_fact(self, tmpdir, standalone_factfile, capsys):
        hack()
        standalone_factfile = imp.load_source('factfile', standalone_factfile)
        standalone_factfile.main()
        out, err = capsys.readouterr()
        assert "out: hello, world!" in out


class TestArgParsing:
    def test_should_parse_splited_arguments(self, capsys):
        hack()
        sys.argv = ['factory.py', "run", "echo 'hello world!'"]
        factory.main.main()
        out, err = capsys.readouterr()
        assert "hello world!" in out

    def test_should_execute_many_functions(self, capsys):
        hack()
        sys.argv = ['factory.py', "run", "echo 'hello world!'", "run", "echo 'hello world!'"]
        factory.main.main()
        out, err = capsys.readouterr()
        assert out.count('hello world!') == 4

    def test_should_parse_many_arguments(self, capsys):
        hack()
        sys.argv = ['factory.py', "-nr", "echo 'hello world!'"]
        factory.main.main()
        out, err = capsys.readouterr()
        assert out == ''
        with open('factory.log', 'r') as f:
            assert "hello world!" in f.readlines()[-2]

    def test_should_parallel_executing(self, capfd):
        hack()
        sys.argv = ['factory.py', '-p', "run", "sleep 1; echo -n 'world!'", "run", "echo -n 'hello'"]
        factory.main.main()
        out, err = capfd.readouterr()
        assert out.rfind('out: hello') < out.rfind('out: world!')

    def test_should_execute_factfile(self, tmpdir, factfile, capsys):
        hack()
        sys.argv = ['factory.py', '--factfile', factfile, 'hello_fact']
        factory.main.main()
        out, err = capsys.readouterr()
        assert "this if factfile" in out

    def test_should_execute_fabfile(self, tmpdir, fabfile, capsys):
        hack()
        sys.argv = ['factory.py', '--fabfile', fabfile, 'hello_fab']
        factory.main.main()
        out, err = capsys.readouterr()
        assert "this if fabfile" in out

    def test_should_set_username(self, capsys):
        hack()
        sys.argv = ['factory.py', '--user', 'user', '']
        factory.main.main()
        # set defaults back
        from getpass import getuser
        factory.main.envs.common.user = getuser()
        out, err = capsys.readouterr()
        assert "user@localhost" in out

    def test_should_set_ssh_port(self, capsys):
        hack()
        sys.argv = ['factory.py', '-H', 'test', '--port', '111111', '']
        factory.main.main()
        # set defaults back
        factory.main.envs.common.hosts = ['localhost']
        factory.main.envs.common.ssh_port = 22
        out, err = capsys.readouterr()
        assert "Bad port '111111'" in out


class TestFeedback:
    def test_should_write_command_stdout_to_sys_stdout(self, capsys):
        hack()
        sys.argv = ['factory.py', "run:echo 'hello world!'"]
        factory.main.main()
        out, err = capsys.readouterr()
        assert "hello world!" in out

    def test_should_write_command_stderr_to_sys_stdout(self, capsys):
        hack()
        sys.argv = ['factory.py', 'run:qwertyuiop']
        factory.main.main()
        out, err = capsys.readouterr()
        assert "/bin/sh: 1: qwertyuiop: not found" in out

    def test_should_communicate_with_stdin(self, capsys):
        hack()
        from subprocess import Popen, PIPE, call
        try:
            call("./factory/main.py")
            p = Popen('echo "hello world!" | ./factory/main.py -p -H localhost,127.0.0.1 "python -c \'print raw_input()\'"',
                    stdout=PIPE, stderr=PIPE, shell=True
            )
        except OSError:
            p = Popen('echo "hello world!" | fact -p -H localhost,127.0.0.1 "python -c \'print raw_input()\'"',
                stdout=PIPE, stderr=PIPE, shell=True
            )
        out, err = p.communicate()
        assert out.find("out: hello world!", (out.find("out: hello world!") + 1)) != -1

    def test_should_write_logs(self):
        hack()
        sys.argv = ['factory.py', "run", "echo 'hello world!'"]
        factory.main.main()
        with open('factory.log', 'r') as f:
            assert "out: hello world!" in f.readlines()[-1]

    def test_should_only_write_logs(self, capsys):
        hack()
        sys.argv = ['factory.py', "-n", "run", "echo 'hello world!'"]
        factory.main.main()
        out, err = capsys.readouterr()
        assert out == ''
        with open('factory.log', 'r') as f:
            assert "out: hello world!" in f.readlines()[-1]

    def test_should_work_with_unicode(self, capsys):
        hack()
        sys.argv = ['factory.py', "echo 'привет, мир!'"]
        factory.main.main()
        out, err = capsys.readouterr()
        assert u"out: привет, мир!" in out

    def test_should_write_command_stderr_to_sys_stdout(self, capsys):
        hack()
        sys.argv = ['factory.py', 'run:qwertyuiop,err_to_out=True']
        factory.main.main()
        out, err = capsys.readouterr()
        assert "/bin/sh: 1: qwertyuiop: not found" in out

    def test_should_load_config(self, tmpdir, config, capsys):
        hack()
        sys.argv = ['factory.py', '--config', config, "run::echo 'hello world!'"]
        factory.main.main()
        # set defaults back
        factory.main.envs.common.split_function = ':'
        out, err = capsys.readouterr()
        assert "run::echo 'hello world!'" not in out
        assert "hello world!" in out

    def test_should_hide_errors(self, capsys):
        hack()
        sys.argv = ['factory.py', "run:echo 'hello world!',err_to_out=True"]
        factory.main.main()
        out, err = capsys.readouterr()
        assert "can't process stderr" not in err

    def test_should_show_errors(self, capsys):
        hack()
        sys.argv = ['factory.py', '--show-errors', "run:echo 'hello world!',err_to_out=True"]
        factory.main.main()
        out, err = capsys.readouterr()
        #print err
        #assert "can't process stderr" in err
        # set defaults back
        factory.main.envs.common.show_errors = False

    def test_should_write_stdin_into_log(self, capsys):
        hack()
        from subprocess import Popen, PIPE, call
        try:
            call("./factory/main.py")
            p = Popen('echo "hello world!" | ./factory/main.py "python -c \'print raw_input()\'"',
                    stdout=PIPE, stderr=PIPE, shell=True
            )
        except OSError:
            p = Popen('echo "hello world!" | fact "python -c \'print raw_input()\'"',
                stdout=PIPE, stderr=PIPE, shell=True
            )
        out, err = p.communicate()
        assert 'in: hello world!' in out

    def test_should_not_write_stdin_into_log(self, capsys):
        hack()
        from subprocess import Popen, PIPE, call
        try:
            call("./factory/main.py")
            p = Popen('echo "hello world!" | ./factory/main.py --no-stdin-cache "python -c \'print raw_input()\'"',
                    stdout=PIPE, stderr=PIPE, shell=True
            )
        except OSError:
            p = Popen('echo "hello world!" | fact --no-stdin-cache "python -c \'print raw_input()\'"',
                stdout=PIPE, stderr=PIPE, shell=True
            )
        out, err = p.communicate()
        assert 'in: hello world!' in out

class TestLoadFilesFromHomeDirectory:
    def test_should_load_factfile(self, tmpdir, factfile, capsys):
        hack()
        sys.argv = ['factory.py', 'hello_fact']
        with factory.context_managers.set_common_env(home_directory=str(tmpdir)):
            factory.main.main()
        out, err = capsys.readouterr()
        assert "this if factfile" in out

    def test_should_load_fabfile(self, tmpdir, fabfile, capsys):
        hack()
        sys.argv = ['factory.py', 'hello_fab']
        with factory.context_managers.set_common_env(home_directory=str(tmpdir)):
            factory.main.main()
        out, err = capsys.readouterr()
        assert "this if fabfile" in out

    def test_should_load_common_config(self, tmpdir, config, capsys):
        hack()
        sys.argv = ['factory.py', "run::echo 'hello world!'"]
        with factory.context_managers.set_common_env(home_directory=str(tmpdir)):
            factory.main.main()
        # set defaults back
        factory.main.envs.common.split_function = ':'
        out, err = capsys.readouterr()
        assert "run::echo 'hello world!'" not in out
        assert "hello world!" in out


if __name__ == '__main__':
    pytest.main()
