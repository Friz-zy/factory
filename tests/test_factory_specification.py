#!/usr/bin/env python
# -*- coding: utf-8 -*- 
"""Requirements specification for the factory"""

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
    sys.argv = ['factory.py', "run:echo \"hello world!\""]
    factory.main()
    out, err = capsys.readouterr()
    assert "hello world!" in out


def test_should_write_command_stderr_to_sys_stderr(capsys):
    sys.argv = ['factory.py', 'run:qwertyuiop']
    factory.main()
    out, err = capsys.readouterr()
    assert "/bin/sh: 1: qwertyuiop: not found" in err
    

if __name__ == '__main__':
    pytest.main()
