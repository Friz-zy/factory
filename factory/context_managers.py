#!/usr/bin/env python
# coding=utf-8
"""Context managers for use with the python 'with' statement."""

# This file is part of https://github.com/Friz-zy/factory

import sys
from contextlib import contextmanager, nested
from main import logging, envs
from state import AttributedDict


def hide(*args):
    """Set envs.common.interactive and/or envs.common.show_errors to False.

    Alias to show(*args, show=False).
    If no one mode is specified, set to False both.

    Args:
    'stdout' (str): set envs.common.interactive to False
    'stderr' (str): envs.common.show_errors to False

    """
    return show(*args, show=False)


def show(*args, **kwargs):
    """Set envs.common.interactive and/or envs.common.show_errors to True.

    If no one mode is specified, set to True both.

    Args:
    'stdout' (str): set envs.common.interactive to True
    'stderr' (str): envs.common.show_errors to True
    show (bool): uses as value for options, default is True

    """
    show = kwargs.pop('show', True)
    kwargs = {}
    if args:
        if 'stdout' in args:
            kwargs['interactive'] = show
        if 'stderr' in args:
            kwargs['show_errors'] = show
    else:
        kwargs['interactive'] = show
        kwargs['show_errors'] = show
    return set_common_env(**kwargs)


@contextmanager
def set_common_env(*args, **kwargs):
    """Context manager that set envs.common atributes.

    If one of args will be 'clean' = False, envs.common
    will be saved in updated state.
    Else envs.common will be reverted to previous state
    after 'with' statement.

    Args:
      *args (tuple):
        if argument is dict, env.common will be updated by this dict
        and if argument is function, env.common will be updated by executing this function
        and if argument is just number, string or object, it will be used as key with value = True
      **kwargs (dict): env.common will be updated by this dict

    Returns:
      envs.common object with most of all atributes

    Examples:
      >>> with set_common_env('test', test1='test1') as common_env:
      ...     common_env.__dict__ # doctest: +NORMALIZE_WHITESPACE
      {'test1': 'test1',
      'functions': {},
      'ssh_port_option': '-p',
      'split_user': '@',
      'split_function': ':',
      'ssh_port': 22,
      'scp_binary': 'scp',
      'user': ...,
      'arithmetic_symbols': ('=', '!', '>', '<', '+', '-', '*', '/', '%'),
      'split_port': ':',
      'scp_port_option': '-P',
      'hosts': ['localhost'],
      'default_shell': 'sh',
      'split_args': ',',
      'test': True,
      'ssh_binary': 'ssh',
      'split_hosts': ',',
      'parallel': False,
      'localhost': ['localhost', '127.0.0.1', ...],
      'interactive': True}

    """
    logging.debug('initializing of set_common_env')
    logging.debug('arguments and another locals: %s', locals())
    try:
        dict={}
        if args:
            for a in args:
                if type(a) is dict:
                    dict.update(a)
                elif callable(a):
                    try:
                        dict.update(a())
                    except:
                        logging.warning()
                        continue
                else:
                    dict[a] = True
        if kwargs:
            dict.update(kwargs)
        clean = dict.pop('clean', True)
        if clean:
            old = {}
            new = []
            for key in dict.keys():
                try:
                    old [key] = envs.common[key]
                except KeyError:
                    new.append(key)
        envs.common.update(dict)
        yield envs.common
    finally:
        if clean:
            logging.debug('reverted global envs.common to previous state')
            envs.common.update(old)
            for k in new:
                del envs.common[k]

@contextmanager
def set_connect_env(connect_string, con_args=''):
    """Context manager that set envs.connect atributes.

    Args:
      connect_string (str): [user@]host[:port]
      con_args (str): options for ssh

    Connect_env attibutes:
      connect_string (str): [user@]host[:port]
      user (str): username for connect, default is getpass.getuser()
      host (str): hostname or ip for connect
      port (str): port for connect
      con_args (str): options for ssh
      logger (logging.logger object): logger object for this connect
      check_is_root (bool): True if connected as root, else False

    Returns:
      envs.connect object with most of all atributes


    Examples:
      >>> from api import *
      >>> with set_connect_env('user@host:port', '') as connect_env:
      ...     connect_env.__dict__ # doctest: +NORMALIZE_WHITESPACE
      user@host in: id -u
      user@host err: Bad port 'port'
      <BLANKLINE>
      {'check_is_root': False,
      'connect_string': 'user@host:port',
      'con_args': '',
      'host': 'host',
      'user': 'user',
      'logger': ...,
      'port': 'port'}

    """
    logging.debug('initializing of set_connect_env')
    logging.debug('arguments and another locals: %s', locals())
    try:
        # save envs.connect that was before
        old_dict = {}
        old_dict.update(envs.connect.__dict__)

        envs.connect.connect_string = connect_string
        if envs.common.split_user in connect_string:
            envs.connect.user, connect_string = connect_string.split(
                envs.common.split_user
            )
        else:
            envs.connect.user = envs.common.user
        if envs.common.split_port in connect_string:
            envs.connect.host, envs.connect.port = connect_string.split(
                envs.common.split_port
            )
        else:
            envs.connect.host = connect_string
            envs.connect.port = envs.common.ssh_port
        envs.connect.con_args = con_args
        envs.connect.logger = logging.getLogger(
            ''.join((envs.connect.user,
                envs.common.split_user,
                envs.connect.host
            ))
        )
        # add logging to interactive output
        if envs.common.interactive:
            logging.debug('adding logging to interactive output')
            # only info for stdout
            info = logging.StreamHandler(sys.stdout)
            info.addFilter(OnlyOneLevelLogs(logging.INFO))
            info.setFormatter(logging.Formatter('%(name)s %(message)s'))
            envs.connect.logger.addHandler(info)
            # all another to stderr
            error = logging.StreamHandler(sys.stderr)
            error.addFilter(WithoutOneLevelLogs(logging.INFO))
            error.setFormatter(logging.Formatter('%(name)s %(message)s'))
            envs.connect.logger.addHandler(error)
        from operations import check_is_root
        envs.connect.check_is_root = check_is_root()
        logging.debug('envs.connect: %s', envs.connect)
        yield envs.connect
    finally:
        # Reinitialized global envs.connect as AttributedDict class.
        logging.debug('reinitialization global envs.connect as AttributedDict class')
        envs.connect.replace(old_dict)


class OnlyOneLevelLogs(object):
    """Logging handler filter"""
    def __init__(self, level):
        """Initializing of  OnlyOneLevelLogs class.

        Args:
          level (logging level): only this level will be caught

        """
        logging.debug('initializing of OnlyOneLevelLogs class')
        logging.debug('arguments for __init__ and another locals: %s', locals())
        self.level = level

    def filter(self, record):
        """Filtering logging record

        Args:
          record (logging record): record that will be filtered

        """
        return record.levelno == self.level and envs.common.interactive


class WithoutOneLevelLogs(object):
    """Logging handler filter"""
    def __init__(self, level):
        """Initializing of  WithoutOneLevelLogs class.

        Args:
          level (logging level): only this level will not be caught

        """
        logging.debug('initializing of WithoutOneLevelLogs class')
        logging.debug('arguments for __init__ and another locals: %s', locals())
        self.level = level

    def filter(self, record):
        """Filtering logging record

        Args:
          record (logging record): record that will be filtered

        """
        return record.levelno != self.level and envs.common.show_errors
