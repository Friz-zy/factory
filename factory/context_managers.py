#!/usr/bin/env python
# coding=utf-8
"""Context managers for use with the python 'with' statement."""

# This file is part of https://github.com/Friz-zy/factory

import sys
from contextlib import contextmanager, nested
from main import logging, envs
from state import Empty


@contextmanager
def set_global_env(*args, **kwargs):
    """Context manager that set envs.connect atributes.

    Args:
      *args
      **kwargs

    Returns:
      envs.common object with most of all atributes

    Examples:

    """
    logging.debug('initializing of set_global_env')
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
        logging.debug('reinitialization global envs.connect as Empty class')
        if clean:
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
        # Reinitialized global envs.connect as Empty class.
        logging.debug('reinitialization global envs.connect as Empty class')
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
