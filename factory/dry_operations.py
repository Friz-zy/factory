#!/usr/bin/env python
# coding=utf-8
"""Dummy functions to replace functions from operations module.

  It's a new module because i think that add dry-run cases to original operations
  will be ugly and dirty.
  Yes, i know, that separate module will be required more time energy for back
  compability with original operations

"""

# This file is part of https://github.com/Friz-zy/factory

from __future__ import with_statement

import os
import re
from main import envs
from operations import write_message_to_log, run, command_patching_for_sudo

def run(command, use_sudo=False, user='', group='', freturn=False, err_to_out=False, input=None, use_which=True, sumout='', sumerr='', status=0):
    """Dummy executing command on host via ssh or subprocess.

    If use_which is not False, original run command will be executed with 'which' command,
    and it returns will be used as new sumout, somerr, status if original is not exists.

    Args:
      command (str): command for executing
      use_sudo (bool): running with sudo prefix if True and current user not root, default is False
      user (str): username for sudo -u prefix
      group (str): group for sudo -g prefix
      freturn (bool): return tuple if True, else return str, default is False
      err_to_out (bool): redirect stderr to stdout if True, default is False
      input (str or tuple of str): str will be flushed to stdin after executed command, default is None
      use_which (bool): tries to strip command line and and run 'which' for each binary, default is True
        works only for unix
      sumout (str): fake string that contained all stdout messages, default is ''
      sumerr (str): fake string that contained all stderr, default is ''
      status (int): fake return code of command, default is 0

    Return:
      str if freturn is False: string that contained all stdout messages
      tuple if freturn is True:
        string that contained all stdout messages
        string that contained all stderr
        int that mean return code of command

    """
    logger = envs.connect.logger
    logger.debug('executing dry-run function')
    logger.debug('arguments for executing and another locals: %s', locals())

    original_command = command
    command = command_patching_for_sudo(command, use_sudo, user, group)

    # logging
    write_message_to_log(command, 'dry-in: ')

    if use_which:
        # separate sudo modificator
        if original_command != command:
            st = command.find(original_command)
            command = command[:st] + '|' + command[st:]

        ncommand = ''
        command = re.split('\\&|\\||\\;', command)
        for part in command:
            ncommand += '{} {}; '.format(
                envs.common.which_binary,
                re.findall(r"[\w']+", part)[0]
            )

        # import current run implementation
        try:
            run = envs.common.functions['run']
        except KeyError:
            from operations import run

        if not (sumout and sumerr and status):
            sumout, sumerr, status = run(ncommand, freturn=True, err_to_out=err_to_out, force=True)
        else:
            run(ncommand, err_to_out=err_to_out, force=True)

    if freturn:
        logger.debug('return sumout %s, sumerr %s, status %s', sumout, sumerr, status)
        return (sumout, sumerr, status)
    logger.debug('return sumout %s', sumout)
    return sumout


def push(src, dst='~/', pull=False, use_test=True, status=0):
    """Dummy copying file or directory.

    If use_test is not False, original run command will be executed with 'test' command,
    and it returns will be used as status if original is not exists.

    Args:
      src (str): local file or directory
      dst (str): destination path, default is '~/'
      pull (bool): copy file from another host to localhost if True, default is False
      use_test (bool): tries to run 'test -e' for each file, default is True
        works only for unix
      status (int): fake return code of command, default is 0

    Return:
      int that mean return code of command:
        exception? 0 : errno on localhost
        status of subprocess with scp

    """
    logger = envs.connect.logger
    logger.debug('executing push function')
    logger.debug('arguments for executing and another locals: %s', locals())
    if envs.connect.host in envs.common.localhost:
        logger.debug('used shutil.copy*')
        for p in (src, dst):
            if os.path.exists(p):
                logger.debug('os.path.exists(%s) is True', p)
                if os.path.isfile(p):
                    logger.debug('os.path.isfile(%s) is True, used shutil.copy2', p)
                    write_message_to_log('file \'%s\' is exists' % p, 'dry-out: ')
                elif os.path.isdir(p):
                    logger.debug('os.path.isdir(%s) is True, used shutil.copytree', p)
                    write_message_to_log('directory \'%s\' is exists' % p, 'dry-out: ')
            else:
                logger.debug('os.path.exists(%s) is False', p)
                write_message_to_log('path \'%s\' is not exists' % p, 'dry-out: ')
        if not os.path.exists(src) and not status:
            return 2 # errno.ENOENT
        return status

    else:
        logger.debug('used factory.run')
        # import current run implementation
        try:
            run = envs.common.functions['run']
        except KeyError:
            from operations import run
        if pull:
            if use_test:
                command = '{} {}'.format(
                    envs.common.test_binary,
                    src
                )
                if not status:
                    o, e, status = run(command, freturn=True, force=True)
                else:
                    run(command, force=True)
            if os.path.isfile(dst):
                logger.debug('os.path.isfile(dst) is True, used shutil.copy2')
                write_message_to_log('file \'%s\' is exists' % dst, 'dry-out: ')
            elif os.path.isdir(dst):
                logger.debug('os.path.isdir(dst) is True, used shutil.copytree')
                write_message_to_log('directory \'%s\' is exists' % dst, 'dry-out: ')
            else:
                logger.debug('os.path.exists(dst) is False')
                write_message_to_log('path \'%s\' is not exists' % dst, 'dry-out: ')
            return status
        else:
            if os.path.isfile(src):
                logger.debug('os.path.isfile(src) is True, used shutil.copy2')
                write_message_to_log('file \'%s\' is exists' % src, 'dry-out: ')
            elif os.path.isdir(src):
                logger.debug('os.path.isdir(src) is True, used shutil.copytree')
                write_message_to_log('directory \'%s\' is exists' % src, 'dry-out: ')
            else:
                logger.debug('os.path.exists(src) is False')
                write_message_to_log('path \'%s\' is not exists' % src, 'dry-out: ')
            if use_test:
                command = '{} {}'.format(
                    envs.common.test_binary,
                    dst
                )
                run(command, force=True)
            if not os.path.exists(src) and not status:
                return 2 # errno.ENOENT
            return status


def run_script(local_file, binary=None, freturn=False, err_to_out=False, input=None, use_which=True, sumout='', sumerr='', status=0):
    """Dummy excecuting script.

    If use_which is not False, original run command will be executed with 'which' command,
    and it returns will be used as new sumout, somerr, status if original is not exists.

    Args:
      local_file (str): script on localhost for executing
      binary (str): shell for executing, first line of script or 'sh -s'
      freturn (bool): return tuple if True, else return str, default is False
      err_to_out (bool): redirect stderr to stdout if True, default is False
      input (str): str will be flushed to stdin after executed command, default is None
      use_which (bool): tries to strip command line and and run 'which' for each binary, default is True
        works only for unix
      sumout (str): fake string that contained all stdout messages, default is ''
      sumerr (str): fake string that contained all stderr, default is ''
      status (int): fake return code of command, default is 0


    Return:
      str if freturn is False: string that contained all stdout messages
      tuple if freturn is True:
        string that contained all stdout messages
        string that contained all stderr
        int that mean return code of command
    """
    logger = envs.connect.logger
    host_string = ''.join((envs.connect.user,
                           '@',
                           envs.connect.host))
    logger.debug('executing run_script function')
    logger.debug('arguments for executing and another locals: %s', locals())

    if os.path.isfile(local_file):
        logger.debug('os.path.isfile(local_file) is True, used shutil.copy2')
        write_message_to_log('file \'%s\' is exists' % local_file, 'dry-out: ')
    else:
        write_message_to_log('path \'%s\' is not exists' % local_file, 'dry-out: ')
        if not status:
            status = 2 # errno.ENOENT

    if not binary:
        logger.debug('trying get binary from script file')
        try:
            with open(local_file) as f:
                l = f.readline()
            logger.debug('firs line from script file: %s', l)
            if l.startswith('#'):
                binary = l.strip()[2:]
                logger.debug('binary: %s', binary)
            else:
                binary = 'sh -s'
                logger.debug('used default binary: %s', binary)
        except IOError:
            binary = 'sh -s'
            logger.debug('used default binary: %s', binary)

    command = binary + " < " + local_file

    # open new connect
    logger.debug('run command: %s', command)
    return run(command, err_to_out=err_to_out, use_which=use_which, sumout=sumout, sumerr=sumerr, status=status)
