#!/usr/bin/env python
# coding=utf-8
"""Context managers for use with the python 'with' statement."""

# This file is part of https://github.com/Friz-zy/factory

import sys
from contextlib import contextmanager
from main import logging

@contextmanager
def set_connect_env(connect_string, con_args=''):
    """Context manager that set connect_env atributes.

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
      connect_env object with most of all atributes


    Examples:
      >>> load_config()
      >>> with set_connect_env('user@host:port', '') as connect_env:
      ...     connect_env.__dict__ # doctest: +NORMALIZE_WHITESPACE
      {'connect_string': 'user@host:port',
      'con_args': '',
      'check_is_root': False,
      'host': 'host',
      'user': 'user',
      'logger': ...,
      'port': 'port'}

    """
    logging.debug('initializing of set_connect_env')
    logging.debug('arguments and another locals: %s', locals())
    try:
        from main import global_env, connect_env
        from state import Empty

        # save connect_env that was before
        old_dict = {}
        old_dict.update(connect_env.__dict__)

        connect_env.connect_string = connect_string
        if global_env.split_user in connect_string:
            connect_env.user, connect_string = connect_string.split(
                global_env.split_user
            )
        else:
            connect_env.user = global_env.user
        if global_env.split_port in connect_string:
            connect_env.host, connect_env.port = connect_string.split(
                global_env.split_port
            )
        else:
            connect_env.host = connect_string
            connect_env.port = global_env.ssh_port
        connect_env.con_args = con_args
        connect_env.logger = logging.getLogger(
            ''.join((connect_env.user,
                global_env.split_user,
                connect_env.host
            ))
        )
        # add logging to interactive output
        if global_env.interactive:
            logging.debug('adding logging to interactive output')
            # only info for stdout
            info = logging.StreamHandler(sys.stdout)
            info.addFilter(OnlyOneLevelLogs(logging.INFO))
            info.setFormatter(logging.Formatter('%(name)s %(message)s'))
            connect_env.logger.addHandler(info)
            # all another to stderr
            error = logging.StreamHandler(sys.stderr)
            error.addFilter(WithoutOneLevelLogs(logging.INFO))
            error.setFormatter(logging.Formatter('%(name)s %(message)s'))
            connect_env.logger.addHandler(error)
        from operations import check_is_root
        connect_env.check_is_root = check_is_root()
        logging.debug('connect_env: %s', connect_env)
        yield
    finally:
        # Reinitialized global connect_env as Empty class.
        logging.debug('reinitialization global connect_env as Empty class')
        connect_env.replace(old_dict)


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
        return record.levelno == self.level


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
        return record.levelno != self.level
