#!/usr/bin/env python
# coding=utf-8
"""Global config settings.

Attributes:
  envs (gevent.local local object)
    common (AttributedDict class object): global class instance for global options
      interactive (bool): False if --non-interactive given, else True
      show_errors (bool): copy factory warnings and errors into stdout (works with and without interactive mode), default is False
      parallel (bool): True if --parallel given, else False
      ask_passwd (bool): open secure invite shell for passwords, default is False
      functions (dict): dict with all functions, default is {}
      localhost (tuple): tuple with all names and ip of localhost, default is ['localhost', '127.0.0.1', socket.gethostname()]
      split_function (str): splitter between function and args, default is ':'
      split_args (str): splitter between args, default is ','
      arithmetic_symbols (list): list of arithmetic symbols, default is ('=', '!', '>', '<', '+', '-', '*', '/', '%')
      split_hosts (str): splitter between hosts connection strings, default is ','
      split_user (str): splitter between user and host, default is '@'
      split_port (str): splitter between host and port, default is ':'
      default_shell (str): default 'sh'
      ssh_binary (str): path to ssh binary, default is 'ssh'
      ssh_port (int or str): ssh port for connections, default is '22'
      ssh_port_option (str): ssh port option, default is '-p'
      ssh_args (str): ssh additional arguments, default is '-tt'
      scp_binary (str): path to scp binary, default is 'scp'
      scp_port_option (str): scp port option, default is '-P'
      scp_args (str): scp additional arguments, default is ''
      user (str): username for ssh login, default is current user (via getuser())
      hosts (tuple): tuple with connection strings like user@host:port, default is ['localhost']
      home_directory (str): path to default factory directory,
        uses for searching config and another files as and current directory,
        default is join(expanduser('~'), '.factory')
      store_stdin (bool): store messages from sys.stdin into log except password promts, default is True
      dry_run (bool): use dummy operations from dry_operations, default is False
      which_binary (str): binary for checking executing binary in dry-run mod, default is 'which',
        for windows 'where.exe' can be used manually
      test_binary (str): binary for checking file or directory existing in dry-run mod, default is 'test -e'

    connect (AttributedDict class object): global class instance for connect environment
      connect_string (str): [user@]host[:port]
      user (str): username for connect, default is getpass.getuser()
      host (str): hostname or ip for connect
      port (str): port for connect
      con_args (str): options for ssh
      logger (logging.logger object): logger object for this connect
      check_is_root (bool): True if connected as root, else False

  stdin_queue (gevent queue object): global queue for sys.stdin messages in interactive mode, default is gevent.queue.Queue()
  connects (dict): dict with already exists envs.connect, used only by set_connect_env context manager

"""

# This file is part of https://github.com/Friz-zy/factory

from os.path import join, expanduser
import gevent.queue
from gevent.local import local
from socket import gethostname
from getpass import getuser


class AttributedDict(dict):
    def __init__(self, dict={}):
        self.__dict__ = dict

    def __str__(self):
        return str(self.__dict__)

    def __getitem__(self,key):
        return self.__dict__[key]

    def __setitem__(self,key,value):
        self.__dict__[key] = value

    def __delitem__(self, item):
        del self.__dict__[item]

    def update(self, dict):
        self.__dict__.update(dict)

    def clean(self):
        self.__dict__ = {}

    def replace(self, dict):
        self.__dict__ = dict


# default variables
envs = local()

envs.common = AttributedDict(
    {
    'interactive': True,
    'show_errors': False,
    'parallel': False,
    'ask_passwd': False,
    'functions': {},
    'localhost': [
        'localhost',
        '127.0.0.1',
        gethostname(),
        ],
    'split_function': ':',
    'split_args': ',',
    'arithmetic_symbols': (
        '=', '!', '>', '<', 
        '+', '-', '*', '/', '%'
        ),
     'split_hosts': ',',
     'split_user': '@',
     'split_port': ':',
     'default_shell': 'sh',
     'ssh_binary': 'ssh',
     'ssh_port': 22,
     'ssh_port_option': '-p',
     'ssh_args': '-tt',
     'scp_binary': 'scp',
     'scp_port_option': '-P',
     'scp_args': '',
     'user': getuser(),
     'hosts': ['localhost'],
     'home_directory': join(expanduser('~'), '.factory'),
     'store_stdin': True,
     'dry_run': False,
     'which_binary': 'which',
     'test_binary': 'test -e',
     }
)

envs.connect = AttributedDict()

stdin_queue = gevent.queue.Queue()
connects = {}
