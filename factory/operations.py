#!/usr/bin/env python
# coding=utf-8
"""Functions for execution like run('echo "hello, world!"')."""

# This file is part of https://github.com/Friz-zy/factory

from __future__ import with_statement

import os
import sys
from copy import copy
from shutil import copy2, copytree
import gevent
from gevent.subprocess import Popen, PIPE, STDOUT
from main import logging, envs, stdin_queue
from context_managers import set_connect_env

def run(command, use_sudo=False, user='', group='', freturn=False, err_to_out=False, input=None):
    """Execute command on host via ssh or subprocess.

    Args:
      command (str): command for executing
      use_sudo (bool): running with sudo prefix if True and current user not root, default is False
      user (str): username for sudo -u prefix
      group (str): group for sudo -g prefix
      freturn (bool): return tuple if True, else return str, default is False
      err_to_out (bool): redirect stderr to stdout if True, default is False
      input (str): str will be flushed to stdin after executed command, default is None

    Return:
      str if freturn is False: string that contained all stdout messages
      tuple if freturn is True:
        string that contained all stdout messages
        string that contained all stderr
        int that mean return code of command

    """
    logger = envs.connect.logger
    interactive = envs.common.interactive
    parallel = envs.common.parallel
    host_string = ''.join((envs.connect.user,
                           '@',
                           envs.connect.host))
    logger.debug('executing run function')
    logger.debug('arguments for executing and another locals: %s', locals())
    # run as root
    logger.debug('case use_sudo')
    if use_sudo:
        if not envs.connect.check_is_root:
            if 'sudo' not in command.split():
                command = " ".join(('sudo', command))
        logger.debug('command: %s', command)
    # switching user
    logger.debug('case user')
    if user:
        if 'sudo' not in command.split():
            command = " ".join(('sudo -u %s -s' % user, command))
        else:
            command.replace('sudo', 'sudo -u %s' % user)
        logger.debug('command: %s', command)
    # switching group
    logger.debug('case group')
    if group:
        if 'sudo' not in command.split():
            command = " ".join(('sudo -g %s -s' % group, command))
        else:
            command.replace('sudo', 'sudo -g %s' % group)
        logger.debug('command: %s', command)

    # logging
    try:
        logger.info('in: %s', unicode(command, "UTF-8"))
    except TypeError:
        logger.info('in: %s', command)

    stderr = PIPE
    if err_to_out:
        stderr = STDOUT
    logger.debug('stderr: %s', stderr)
    # open new connect
    if envs.connect.host in envs.common.localhost:
        logger.debug('executing command %s with shell=True', command)
        p = Popen(command, stdout=PIPE, stderr=stderr, stdin=PIPE, shell=True)
    else:
        scommand = [
            envs.common.ssh_binary,
            envs.common.ssh_port_option,
            str(envs.connect.port),
            host_string,
            envs.connect.con_args,
            command
        ]
        logger.debug('executing command %s', scommand)
        p = Popen(scommand, stdout=PIPE, stderr=stderr, stdin=PIPE)
    # flush input
    if input:
        input = str(input)
        if input[-1] not in ('\n', '\r'):
            input += '\n'
        logger.debug('flushing input %s', input)
        p.stdin.write(input)
        p.stdin.flush()
    # run another command
    if parallel:
        gevent.sleep(0)
        logger.debug('run another command with gevent.sleep(0)')
    # processing std loop
    threads = []
    if interactive:
        args = (p, copy(envs.common), copy(envs.connect))
        gin = gevent.spawn(in_loop, *args)
        logger.debug('executing in_loop with args %s', args)
        threads.append(gin)

    args = (p, copy(envs.common), copy(envs.connect))
    gout = gevent.spawn(out_loop, *args)
    logger.debug('executing out_loop with args %s', args)
    threads.append(gout)

    args = (p, copy(envs.common), copy(envs.connect))
    gerr = gevent.spawn(err_loop, *args)
    logger.debug('executing err_loop with args %s', args)
    threads.append(gerr)

    gevent.joinall(threads)
    logger.debug('child process has terminated with status %s', p.returncode)
    #TODO: check returncode if returncode==None
    sumout = gout.value
    sumerr = gerr.value
    status = p.returncode
    if p.poll() is None:
        p.terminate()
        p.kill()
    if freturn:
        logger.debug('return sumout %s, sumerr %s, status %s', sumout, sumerr, status)
        return (sumout, sumerr, status)
    logger.debug('return sumout %s', sumout)
    return sumout


def out_loop(p, common_env, connect_env):
    """Loop for command stdout.

    Check executing command stdout and put messages to log and sys.stdout.

    Hack for greenlets:
      common_env its copy of envs.common
      connect_env its copy of envs.connect

    Args:
      p (Popen object): executing command
      common_env (AttributedDict class object): global class instance for global options
      connect_env (AttributedDict class object): global class instance for connect environment

    Return:
      str: string that contained all stdout messages

    """
    sout = ' '
    sumout = ''
    envs.common = common_env
    envs.connect = connect_env
    logger = envs.connect.logger
    logger.debug('executing out_loop function')
    logger.debug('arguments for executing and another locals: %s', locals())
    while sout or p.poll() is None:
        logger.debug('new iteration of reading stdout')
        try:
            sout = p.stdout.readline()
        except AttributeError:
            logger.error("can't process stdout", exc_info=True)
            return ''
        if sout:
            sumout += sout
            # remove \n because logger sum it too
            sout = sout.rstrip()
            try:
                logger.info('out: %s', unicode(sout, "UTF-8"))
            except TypeError:
                logger.info('out: %s', sout)
            #TODO: y\n; password
    logger.debug('return sumout %s', sumout)
    return sumout


def err_loop(p, common_env, connect_env):
    """Loop for command stderr.

    Check executing command stderr and put messages to log and sys.stderr.

    Hack for greenlets:
      common_env its copy of envs.common
      connect_env its copy of envs.connect

    Args:
      p (Popen object): executing command
      common_env (AttributedDict class object): global class instance for global options
      connect_env (AttributedDict class object): global class instance for connect environment

    Return:
      str: string that contained all stderr messages

    """
    serr = ' '
    sumerr = ''
    envs.common = common_env
    envs.connect = connect_env
    logger = envs.connect.logger
    logger.debug('executing err_loop function')
    logger.debug('arguments for executing and another locals: %s', locals())
    while serr or p.poll() is None:
        logger.debug('new iteration of reading stderr')
        try:
            serr = p.stderr.readline()
        except AttributeError:
            logger.error("can't process stderr", exc_info=True)
            return ''
        if serr:
            sumerr += serr
            try:
                logger.info('err: %s', unicode(serr, "UTF-8"))
            except TypeError:
                logger.info('err: %s', serr)
    logger.debug('return sumerr %s', sumerr)
    return sumerr


def in_loop(p, common_env, connect_env):
    """Loop for command stdin.

    Check global stdin queue and put lines from it to command stdin.

    Hack for greenlets:
      common_env its copy of envs.common
      connect_env its copy of envs.connect

    Args:
      p (Popen object): executing command
      common_env (AttributedDict class object): global class instance for global options
      connect_env (AttributedDict class object): global class instance for connect environment

    """
    lin = 0
    envs.common = common_env
    envs.connect = connect_env
    logger = envs.connect.logger
    logger.debug('executing in_loop function')
    logger.debug('arguments for executing and another locals: %s', locals())
    while p.poll() is None:
        logger.debug('new iteration of reading global messaging queue')
        try:
            if stdin_queue.qsize() > lin:
                queue = stdin_queue.copy()
                qs = queue.qsize()
                logger.debug('local queue %s with len %s', queue, qs)
                for i, l in enumerate(queue):
                    if i >= lin:
                        # TODO: crossystem end of line \n \r \nr
                        logger.debug('flush %s to stdin', l)
                        p.stdin.write(l)
                        p.stdin.flush()
                    if queue.qsize() == 0:
                        break
                lin = qs
        except AttributeError:
            #logger.warning("can't process global stdin", exc_info=True)
            break
        gevent.sleep(0)

def sudo(command, user='', group='', freturn=False, err_to_out=False, input=None):
    """sudo is alias for run(use_sudo=True).

    Args:
      command (str): command for executing
      user (str): username for sudo -u prefix
      group (str): group for sudo -g prefix
      freturn (bool): return tuple if True, else return str, default is False
      err_to_out (bool): redirect stderr to stdout if True, default is False
      input (str): str will be flushed to stdin after executed command, default is None

    Return:
      str if freturn is False: string that contained all stdout messages
      tuple if freturn is True:
        string that contained all stdout messages
        string that contained all stderr
        int that mean return code of command

    """
    logger = envs.connect.logger
    logger.debug('executing sudo function')
    logger.debug('arguments for executing and another locals: %s', locals())
    return run(command, use_sudo=True, user=user, group=group, freturn=freturn, err_to_out=err_to_out, input=input)


def local(command, use_sudo=False, user='', group='', freturn=False, err_to_out=False, input=None):
    """Execute command on localhost via subprocess.

    Args:
      command (str): command for executing
      use_sudo (bool): running with sudo prefix if True and current user not root, default is False
      user (str): username for sudo -u prefix
      group (str): group for sudo -g prefix
      freturn (bool): return tuple if True, else return str, default is False
      err_to_out (bool): redirect stderr to stdout if True, default is False
      input (str): str will be flushed to stdin after executed command, default is None

    Return:
      str if freturn is False: string that contained all stdout messages
      tuple if freturn is True:
        string that contained all stdout messages
        string that contained all stderr
        int that mean return code of command

    """
    logger = envs.connect.logger
    logger.debug('executing local function')
    logger.debug('arguments for executing and another locals: %s', locals())
    with set_connect_env('localhost', envs.connect.con_args):
        return run(command, use_sudo=use_sudo, user=user, group=group, freturn=freturn, err_to_out=err_to_out, input=input)


def check_is_root():
    """Check uid via running id -u command.

    Return:
      bool: True if current user uid is 0, else False

    """
    logger = envs.connect.logger
    logger.debug('executing check_is_root function')
    logger.debug('arguments for executing and another locals: %s', locals())
    out, err, status = run('id -u', freturn=True)
    logger.debug('out %s, err %s, status %s', out, err, status)
    if not status:
        try:
            return not int(out)
        except ValueError:
            return False
    return False


def push(src, dst='~/', pull=False):
    """Copying file or directory.

    Copy local file or directory to another host or another localhost place.
    Uses shutil.copy2 and shutil.copytree on localhost and scp (by default)
    with -r option.

    Args:
      src (str): local file or directory
      dst (str): destination path, default is '~/'
      pull (bool): copy file from another host to localhost if True, default is False

    Return:
      int that mean return code of command:
        exception? 0 : 1 on localhost
        status of subprocess with scp

    """
    logger = envs.connect.logger
    host_string = ''.join((envs.connect.user,
                           '@',
                           envs.connect.host))
    logger.debug('executing push function')
    logger.debug('arguments for executing and another locals: %s', locals())
    if envs.connect.host in envs.common.localhost:
        logger.debug('used shutil.copy*')
        if os.path.exists(src):
            logger.debug('os.path.exists(src) is True')
            if os.path.isfile(src):
                logger.debug('os.path.isfile(src) is True, used shutil.copy2')
                try:
                    copy2(src, dst)
                    logger.debug('copying is ok, return zero')
                    return 0
                except:
                    logger.error("can't copy %s to %s", src, dst, info=True)
                    return 1
            else:
                logger.debug('os.path.isfile(src) is False, used shutil.copytree')
                try:
                    copytree(src, dst)
                    logger.debug('copying is ok, return zero')
                    return 0
                except:
                    logger.error("can't copy %s to %s", src, dst, info=True)
                    return 1
        else:
            logger.error("%s path does not exists", src)
            return 1
    else:
        logger.debug('used factory.run')
        if pull:
            command = '-r' + host_string + ':' + src + ' ' + dst
        else:
            command = '-r' + src + ' ' + host_string + ':' + dst
        command = [
            envs.common.scp_binary,
            envs.common.scp_port_option,
            str(envs.connect.port),
            envs.connect.con_args,
            command
        ]

        # open new connect
        logger.debug('run command: %s', command)
        sumout, sumerr, status = local(command, freturn=True)

        logger.debug('return status: %s', status)
        return status

def pull(src, dst='.'):
    """Alias for push(pull=False).

    Args:
      src (str): local file or directory
      dst (str): destination path, default is '.'

    Return:
      int that mean return code of command:
        exception? 0 : 1 on localhost
        status of subprocess with scp

    """
    logger = envs.connect.logger
    logger.debug('executing pull function')
    logger.debug('arguments for executing and another locals: %s', locals())
    return push(src, dst, True)


def get(src, dst='.'):
    """Alias for pull()"""
    logger = envs.connect.logger
    logger.debug('executing get function')
    logger.debug('arguments for executing and another locals: %s', locals())
    return pull(src, dst)


def put(src, dst='~/'):
    """Alias for push"""
    logger = envs.connect.logger
    logger.debug('executing put function')
    logger.debug('arguments for executing and another locals: %s', locals())
    return push(src, dst)


def run_script(local_file, binary=None, freturn=False, err_to_out=False, input=None):
    """Excecute script.

    Execute "binary < local_file" on localhost or via ssh.
    Uses run() function for executing.

    Args:
      local_file (str): script on localhost for executing
      binary (str): shell for executing, first line of script or 'sh -s'
      freturn (bool): return tuple if True, else return str, default is False
      err_to_out (bool): redirect stderr to stdout if True, default is False
      input (str): str will be flushed to stdin after executed command, default is None


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
    if not binary:
        logger.debug('trying get binary from script file')
        with open(local_file) as f:
            l = f.readline()
        logger.debug('firs line from script file: %s', l)
        if l.startswith('#'):
            binary = l.strip()[2:]
            logger.debug('binary: %s', binary)
        else:
            binary = 'sh -s'
            logger.debug('used default binary: %s', binary)

    command = binary + " < " + local_file

    if not envs.connect.host in envs.common.localhost:
        command = ''.join((
            envs.common.ssh_binary,
            envs.common.ssh_port_option,
            str(envs.connect.port),
            host_string,
            envs.connect.con_args,
            command
        ))

    # open new connect
    logger.debug('run command: %s', command)
    return local(command=command, freturn=freturn, err_to_out=err_to_out, input=input)


def open_shell(command=None, shell='/bin/bash -i'):
    """Open shell on host via ssh or subprocess.

    Args:
      command (str): str will be flushed to stdin after opening shell, default is None
      shell (str): shell for opening, default is '/bin/bash -i'

    #FIXME: on localhost after each command moves to background

    """
    logger = envs.connect.logger
    logger.debug('executing open_shell function')
    logger.debug('arguments for executing and another locals: %s', locals())
    run(shell, err_to_out=True, input=command)
