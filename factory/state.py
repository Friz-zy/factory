#!/usr/bin/env python
# coding=utf-8
"""Global config settings.

Attributes:
  global_env (Empty class object): global class instance for global options
    interactive (bool): False if --non-interactive given, else True
    parallel (bool): True if --parallel given, else False
    functions (dict): dict with all functions, default is globals()
    localhost (tuple): tuple with all names and ip of localhost, default is ['localhost', '127.0.0.1', socket.gethostname()]
    split_function (str): splitter between function and args, default is ':'
    split_args (str): splitter between args, default is ','
    arithmetic_symbols (list): list of arithmetic symbols, default is ('=', '!', '>', '<', '+', '-', '*', '/', '%')
    split_hosts (str): splitter between hosts connection strings, default is ','
    split_user (str): splitter between user and host, default is '@'
    split_port (str): splitter between host and port, default is ':'
    default_shell (str): default 'sh'
    ssh_binary (str): path to ssh binary, default is 'ssh'
    ssh_port (int): ssh port for connections, default is '22'
    ssh_port_option (str): ssh port option, default is '-p'
    scp_binary (str): path to scp binary, default is 'scp'
    scp_port_option (str): scp port option, default is '-P'
    stdin_queue (gevent queue object): global queue for sys.stdin messages in interactive mode
    user (str): username for ssh login, default is current user (via getuser())
    hosts (tuple): tuple with connection strings like user@host:port, default is ['localhost']

  connect_env (Empty class object): global class instance for connect environment
    connect_string (str): [user@]host[:port]
    user (str): username for connect, default is getpass.getuser()
    host (str): hostname or ip for connect
    port (str): port for connect
    con_args (str): options for ssh
    logger (logging.logger object): logger object for this connect
    check_is_root (bool): True if connected as root, else False

"""

# This file is part of https://github.com/Friz-zy/factory

from socket import gethostname
from getpass import getuser


class Empty():
    def __init__(self, dict={}):
        self.__dict__ = dict

    def __str__(self):
        return str(self.__dict__)

    def __getitem__(self,key):
        return self.__dict__[key]

    def __setitem__(self,key,value):
        self.__dict__[key] = value

    def update(self, dict):
        self.__dict__.update(dict)

# default variables
global_env = Empty(
    {
    'interactive': True,
    'parallel': False,
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
     'scp_binary': 'scp',
     'scp_port_option': '-P',
     'stdin_queue': None,
     'user': getuser(),
     'hosts': ['localhost'],
     }
)

connect_env = Empty()