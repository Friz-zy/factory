#!/usr/bin/env python
# coding=utf-8
"""
"""
import sys
from main import logging, global_env, connect_env


class set_connect_env():
    """Context manager that set connect_env atributes.

    Connect_env attibutes:
      connect_string (str): [user@]host[:port]
      user (str): username for connect, default is getpass.getuser()
      host (str): hostname or ip for connect
      port (str): port for connect
      con_args (str): options for ssh
      logger (logging.logger object): logger object for this connect
      check_is_root (bool): True if connected as root, else False

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
    def __init__(self, connect_string, con_args=''):
        """Initializing of  set_connect_env class.

        Args:
          connect_string (str): [user@]host[:port]
          con_args (str): options for ssh

        """
        logging.debug('initializing of set_connect_env class')
        logging.debug('arguments for __init__ and another locals: %s', locals())
        self.cs = connect_string
        self.ca = con_args

    def __enter__(self):
        """Set atributes to connect_env object.

        Returns:
          connect_env object with most of all atributes

        """
        logging.debug('set atributes to connect_env object')
        logging.debug('arguments for __enter__ and another locals: %s', locals())
        connect_string = self.cs
        con_args = self.ca
        connect_env.connect_string = connect_string
        if global_env['split_user'] in connect_string:
            connect_env.user, connect_string = connect_string.split(
                global_env['split_user']
            )
        else:
            connect_env.user = global_env['user']
        if global_env['split_port'] in connect_string:
            connect_env.host, connect_env.port = connect_string.split(
                global_env['split_port']
            )
        else:
            connect_env.host = connect_string
            connect_env.port = global_env['ssh_port']
        connect_env.con_args = con_args
        connect_env.logger = logging.getLogger(
            ''.join((connect_env.user,
                global_env['split_user'],
                connect_env.host
            ))
        )
        # add logging to interactive output
        if global_env['interactive']:
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
        return connect_env

    def __exit__(self, type, value, traceback):
        """Reinitialized global connect_env as Empty class.

        FIXME: is it really works?! I doesn't think so...

        """
        logging.debug('reinitialization global connect_env as Empty class')
        from state import Empty
        connect_env = Empty()


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
