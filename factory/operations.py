#!/usr/bin/env python
# coding=utf-8
"""Functions for execution like run('echo "hello, world!"')."""

# This file is part of https://github.com/Friz-zy/factory

from __future__ import with_statement

import os
import sys
from copy import copy
from shlex import split
from getpass import getpass
from shutil import copy2, copytree
import gevent
from gevent.socket import wait_read, timeout
from gevent.subprocess import Popen, PIPE, STDOUT
from main import logging, envs, stdin_queue
from context_managers import set_connect_env

def run(command, use_sudo=False, user='', group='', freturn=False, err_to_out=False, input=None):
    """Execute command on host via ssh or subprocess.

    TODO: check on windows - maybe it will not work on it

    Factory uses pipes for communication with subprocess.
    So, there is no way to use popen and automatically write passwords for ssh and sudo on localhost,
    because "smart" programs like ssh and sudo uses tty directly.
    Also active tty required (needed check it) and for sudo uses "sudo -S".
    Alternatives:
      1) Use paramico like fabric = no ssh sockets.
      2) Use pty.fork, waitpid, execv as pexcpect and sh = only unix, no separated stderr, hard to communicate.
      3) Use ssh-copy-id like sh module recommended = ask passwords only one first time.
      4) Use sshpass like ansible = external dependencies.

    Args:
      command (str): command for executing
      use_sudo (bool): running with sudo prefix if True and current user not root, default is False
      user (str): username for sudo -u prefix
      group (str): group for sudo -g prefix
      freturn (bool): return tuple if True, else return str, default is False
      err_to_out (bool): redirect stderr to stdout if True, default is False
      input (str or tuple of str): str will be flushed to stdin after executed command, default is None

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
                command = " ".join(('sudo -S', command))
        logger.debug('command: %s', command)
    # switching user
    logger.debug('case user')
    if user:
        if 'sudo' not in command.split():
            command = " ".join(('sudo -S -u %s -s' % user, command))
        else:
            command.replace('sudo', 'sudo -u %s' % user)
        logger.debug('command: %s', command)
    # switching group
    logger.debug('case group')
    if group:
        if 'sudo' not in command.split():
            command = " ".join(('sudo -S -g %s -s' % group, command))
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
        ]
        scommand += envs.common.ssh_args.split()
        scommand += envs.connect.con_args.split()
        scommand += [command]
        logger.debug('executing command %s', scommand)
        p = Popen(scommand, stdout=PIPE, stderr=stderr, stdin=PIPE)
    # flush input
    if input:
        if type(input) is str:
            input = [input]
        for s in input:
            s = str(s)
            if s[-1] not in ('\n', '\r'):
                s += '\n'
            logger.debug('flushing input %s', s)
            p.stdin.write(s)
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

    if not err_to_out:
        args = (p, copy(envs.common), copy(envs.connect), True)
        gerr = gevent.spawn(out_loop, *args)
        logger.debug('executing err_loop with args %s', args)
        threads.append(gerr)

    gevent.joinall(threads)
    logger.debug('child process has terminated with status %s', p.returncode)
    #TODO: check returncode if returncode==None
    sumout = gout.value
    sumerr = gerr.value if not err_to_out else ''
    status = p.returncode
    if p.poll() is None:
        p.terminate()
        p.kill()
    if freturn:
        logger.debug('return sumout %s, sumerr %s, status %s', sumout, sumerr, status)
        return (sumout, sumerr, status)
    logger.debug('return sumout %s', sumout)
    return sumout


def out_loop(p, common_env, connect_env, err=False):
    """Loop for command stdout or stderr.

    Check executing command stdout or stderr and put messages to log and sys.stdout.

    Hack for greenlets:
      common_env its copy of envs.common
      connect_env its copy of envs.connect

    Args:
      p (Popen object): executing command
      common_env (AttributedDict class object): global class instance for global options
      connect_env (AttributedDict class object): global class instance for connect environment

    Return:
      str: string that contained all stdout or stderr messages

    """
    line = ''
    char = ' '
    sumout = ''
    win = os.name == 'nt'
    stdout=p.stdout
    prefix='out: '
    if err:
        stdout=p.stderr
        prefix='err: '
    envs.common = common_env
    envs.connect = connect_env
    logger = envs.connect.logger
    logger.debug('executing out_loop function')
    logger.debug('arguments for executing and another locals: %s', locals())
    while char or p.poll() is None:
        logger.debug('new iteration of reading stdout')
        try:
            # wait_read doesn't work on windows
            if win:
                timer = gevent.Timeout.start_new(0.01)
                char = stdout.read(1)
                timer.cancel()
                ready = True
            else:
                wait_read(stdout.fileno(), 0.01)
                char = stdout.read(1)
                ready = True
        except (gevent.Timeout, timeout):
            ready = False
            char = ''
        except AttributeError:
            if err:
                logger.error("can't process stderr", exc_info=True)
            else:
                logger.error("can't process stdout", exc_info=True)
            return ''
        if ready:
            if char:
                sumout += char
                # remove \n because logger sum it too
                if char not in ('\n', '\r'):
                    line += char
                elif line:
                    write_message_to_log(line, prefix)
                    line = ''
            else:
                if line:
                    write_message_to_log(line, prefix)
                    line = ''
        else:
            if line:
                # passwords
                for e in ('[sudo]', 'password', 'Password'):
                    if e in line and envs.common.ask_passwd:
                        p.stdin.write(
                            getpass(
                                '{}{}{} {}{}\n'.format(
                                envs.connect.user,
                                envs.common.split_user,
                                envs.connect.host,
                                prefix,
                                line
                                )
                            )
                        )
                        p.stdin.write('\n')
                        p.stdin.flush()
                        break
                else:
                    write_message_to_log(line, prefix)
                #TODO: y\n
                line = ''
            continue
    logger.debug('return sumout %s', sumout)
    return sumout


def write_message_to_log(message='', prefix=''):
    """Write message to info log.

    Args:
      message (str): message text
      prefix (str): text will be displayed before message without space

    """
    logger = envs.connect.logger
    try:
        logger.info('%s%s', prefix, unicode(message, "UTF-8"))
    except TypeError:
        logger.info('%s%s', prefix, message)


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
        exception? 0 : errno on localhost
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
                except e:
                    logger.error("can't copy %s to %s", src, dst, info=True)
                    return e.errno
            else:
                logger.debug('os.path.isfile(src) is False, used shutil.copytree')
                try:
                    copytree(src, dst)
                    logger.debug('copying is ok, return zero')
                    return 0
                except e:
                    logger.error("can't copy %s to %s", src, dst, info=True)
                    return e.errno
        else:
            logger.error("%s path does not exists", src)
            return 2 # errno.ENOENT
    else:
        logger.debug('used factory.run')
        if pull:
            command = '-r' + host_string + ':' + src + ' ' + dst
        else:
            command = '-r' + src + ' ' + host_string + ':' + dst
        command = ''.join((
            envs.common.scp_binary,
            envs.common.scp_port_option,
            str(envs.connect.port),
            host_string,
            envs.common.scp_args,
            envs.connect.con_args,
            command
        ))

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
            envs.common.ssh_args,
            envs.connect.con_args,
            command
        ))

    # open new connect
    logger.debug('run command: %s', command)
    return local(command, freturn=freturn, err_to_out=err_to_out, input=input)


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
