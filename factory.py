#!/usr/bin/env python
# coding=utf-8
"""Tasks executing via ssh and sh.

Factory provides api for local and nonlocal running of functions,scripts, etc via ssh and sh.
It is proof-of-concept realization of [fabric](https://github.com/fabric/fabric) with a number of differences:
* run() function works in the same way with subprocess.popen under localhost as under ssh connect to remote host
* Factory uses openssh or any another ssh client (you should modified config for this), so you can use all power of ssh sockets
* Factory uses [gevent](https://github.com/surfly/gevent) library for asynchronous executing

Example:
  $ ./factory.py 'echo "hello, world!"'
  $ ./factory.py --host user@host:port run:'uname -a'

Attributes:
  global_env (dict): dict with global options
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

Config files:
  Factory uses standart python logging module,
    so you can set your own config via config file:
      logging.ini, logging.json or logging.yaml
    hardcode logging config:
      format=u'%(asctime)s  %(name)s\t%(levelname)-8s\t%(message)s',
      datefmt='%d %b %Y %H:%M:%S',
      stream=sys.stdout, # will be replacing by filename
      filename= __file__.replace('.py', '.log'), # save log as ./factory.log
      filemode='a',
      level=logging.INFO,

  You can update global_env dict via config file:
    factory.ini, factory.json or factory.yaml
    or --config PATH cli option

"""
from __future__ import with_statement
"""
The MIT License (MIT)

Copyright (c) 2014 Filipp Kucheryavy aka Frizzy <filipp.s.frizzy@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
""" 
__author__ = 'Filipp Frizzy'
__credits__ = ["Filipp Frizzy"]
__license__ = "MIT"
__version__ = ""
__maintainer__ = "Filipp Frizzy"
__email__ = "filipp.s.frizzy@gmail.com"
__status__ = "Development"

import os
import sys

major, minor, micro, releaselevel, serial = sys.version_info
if (major,minor) < (2,5):
    print 'Sorry, but factory requires python 2.5 or highest. Bye!'
    sys.exit(2)

from shutil import copy2, copytree
from socket import gethostname
from getpass import getuser
import logging
import argparse

import gevent
import gevent.queue
from gevent.socket import wait_read
from gevent.subprocess import Popen, PIPE, STDOUT


logging.basicConfig(
    format=u'%(asctime)s  %(name)s\t%(levelname)-8s\t%(message)s',
    datefmt='%d %b %Y %H:%M:%S',
    stream=sys.stdout, # will be replacing by filename
    filename= __file__.replace('.py', '.log'), # save log as ./factory.log
    filemode='a',
    level=logging.INFO,
)

try:
    if os.path.exists('logging.ini'):
        logging.config.fileConfig('logging.ini')
    elif os.path.exists('logging.json'):
        import json
        with open('logging.json', 'r') as f:
            config = json.load(f)
        logging.config.dictConfig(config)
    elif os.path.exists('logging.yaml'):
        import yaml
        with open('logging.yaml', 'r') as f:
            config = yaml.load(f)
        logging.config.dictConfig(config)
except:
    logging.error("can't load logging config, used standart configuration", exc_info=True)

# default variables
global_env = {'interactive': True,
              'parallel': False,
              'functions': {},
              'localhost': [],
              'split_function': ':',
              'split_args': ',',
              'arithmetic_symbols': ('=',
                                     '!',
                                     '>',
                                     '<',
                                     '+',
                                     '-',
                                     '*',
                                     '/',
                                     '%'),
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
              'hosts': ['localhost'],}

class Empty():
    def __init__(self):
        pass

    def __str__(self):
        return self.__dict__

connect_env = Empty()


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
    logger = connect_env.logger
    interactive = global_env['interactive']
    parallel = global_env['parallel']
    host_string = ''.join((connect_env.user,
                           '@',
                           connect_env.host))
    logger.debug('executing run function')
    logger.debug('arguments for executing and another locals: %s', locals())
    # run as root
    logger.debug('case use_sudo')
    if use_sudo:
        if not connect_env.check_is_root:
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
    logger.info('in: %s', unicode(command, "UTF-8"))

    stderr = PIPE
    if err_to_out:
        stderr = STDOUT
    logger.debug('stderr: %s', stderr)
    # open new connect
    if connect_env.host in global_env['localhost']:
        logger.debug('executing command %s with shell=True', command)
        p = Popen(command, stdout=PIPE, stderr=stderr, stdin=PIPE, shell=True)
    else:
        scommand = [
            global_env['ssh_binary'],
            global_env['ssh_port_option'],
            str(connect_env.port),
            host_string,
            connect_env.con_args,
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
        args = (p, logger)
        gin = gevent.spawn(in_loop, *args)
        logger.debug('executing in_loop with args %s', args)
        threads.append(gin)

    args = (p, logger)
    gout = gevent.spawn(out_loop, *args)
    logger.debug('executing out_loop with args %s', args)
    threads.append(gout)

    args = (p, logger)
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


def out_loop(p, logger):
    """Loop for command stdout.

    Check executing command stdout and put messages to log and sys.stdout.

    Args:
      p (Popen object): executing command
      logger (logging.logger object): command logger instance

    Return:
      str: string that contained all stdout messages

    """
    sout = ' '
    sumout = ''
    logger = connect_env.logger
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
            logger.info('out: %s', unicode(sout, "UTF-8"))
            #TODO: y\n; password
    logger.debug('return sumout %s', sumout)
    return sumout


def err_loop(p, logger):
    """Loop for command stderr.

    Check executing command stderr and put messages to log and sys.stderr.

    Args:
      p (Popen object): executing command
      logger (logging.logger object): command logger instance

    Return:
      str: string that contained all stderr messages

    """
    serr = ' '
    sumerr = ''
    logger = connect_env.logger
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
            logger.info('err: %s', unicode(serr, "UTF-8"))
    logger.debug('return sumerr %s', sumerr)
    return sumerr


def in_loop(p, logger):
    """Loop for command stdin.

    Check global stdin queue and put lines from it to command stdin.

    Args:
      p (Popen object): executing command
      logger (logging.logger object): command logger instance (currently not used)

    """
    lin = 0
    logger = connect_env.logger
    logger.debug('executing in_loop function')
    logger.debug('arguments for executing and another locals: %s', locals())
    while p.poll() is None:
        logger.debug('new iteration of reading global messaging queue')
        if global_env['stdin_queue'].qsize() > lin:
            queue = global_env['stdin_queue'].copy()
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
    logger = connect_env.logger
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
    logger = connect_env.logger
    logger.debug('executing local function')
    logger.debug('arguments for executing and another locals: %s', locals())
    with set_connect_env('localhost', connect_env.con_args):
        return run(command, use_sudo=use_sudo, user=user, group=group, freturn=freturn, err_to_out=err_to_out, input=input)


def check_is_root():
    """Check uid via running id -u command.

    Return:
      bool: True if current user uid is 0, else False

    """
    logger = connect_env.logger
    logger.debug('executing check_is_root function')
    logger.debug('arguments for executing and another locals: %s', locals())
    out, err, status = run('id -u', freturn=True)
    logger.debug('out %s, err %s, status %s', out, err, status)
    if not status:
        return not int(out)
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
    logger = connect_env.logger
    host_string = ''.join((connect_env.user,
                           '@',
                           connect_env.host))
    logger.debug('executing push function')
    logger.debug('arguments for executing and another locals: %s', locals())
    if connect_env.host in global_env['localhost']:
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
            global_env['scp_binary'],
            global_env['scp_port_option'],
            str(connect_env.port),
            connect_env.con_args,
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
    logger = connect_env.logger
    logger.debug('executing pull function')
    logger.debug('arguments for executing and another locals: %s', locals())
    return push(src, dst, True)


def get(src, dst='.'):
    """Alias for pull()"""
    logger = connect_env.logger
    logger.debug('executing get function')
    logger.debug('arguments for executing and another locals: %s', locals())
    return pull(src, dst)


def put(src, dst='~/'):
    """Alias for push"""
    logger = connect_env.logger
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
    logger = connect_env.logger
    host_string = ''.join((connect_env.user,
                           '@',
                           connect_env.host))
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

    if not connect_env.host in global_env['localhost']:
        command = ''.join((
            global_env['ssh_binary'],
            global_env['ssh_port_option'],
            str(connect_env.port),
            host_string,
            connect_env.con_args,
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
    logger = connect_env.logger
    logger.debug('executing open_shell function')
    logger.debug('arguments for executing and another locals: %s', locals())
    run(shell, err_to_out=True, input=command)


def main():
    args = parse_cli()
    if args.config_file:
        load_config(args.config_file)
    else:
        load_config()
    logging.debug('executing main function')
    logging.debug('arguments from cli and another locals: %s', locals())
    if args.hosts:
        global_env['hosts'] = args.hosts.split(global_env['split_hosts'])
    # -r -s shortcuts
    if args.sudo:
        args.function.insert(0, 'sudo')
    elif args.run:
        args.function.insert(0, 'run')

    # update globals interactive and parallel from cli
    logging.debug('updating globals interactive and parallel from cli')
    global_env['interactive'] = not args.non_interactive
    global_env['parallel'] = args.parallel

    functions_to_execute = parse_functions(args.function)

    # start of stdin loop
    if global_env['interactive']:
        logging.debug('starting global stdin loop')
        sloop = gevent.spawn(stdin_loop)

    if not global_env['parallel']:
        logging.debug('hosts will be processed one by one')
        for host in global_env['hosts']:
            logging.debug('host %s, functions %s', host, functions_to_execute)
            run_tasks_on_host(host, functions_to_execute)
    else:
        threads = []
        logging.debug('hosts will be processed in parallel')
        for host in global_env['hosts']:
            logging.debug('host %s, functions %s', host, functions_to_execute)
            args = (host, functions_to_execute)
            kwargs = {}
            threads.append(gevent.spawn(run_tasks_on_host, *args, **kwargs))
        gevent.joinall(threads)

    # finish stdin loop
    if global_env['interactive']:
        logging.debug('finishing global stdin loop')
        sloop.kill()


def parse_cli():
    """Use argparse for command line.

    Convert the strings to objects and assign them as attributes of the namespace.

    Return:
      namespace: like Namespace(foo='FOO', x=None)

    """
    logging.debug('parsing %s', sys.argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        'function', nargs='+',
        help='an function with arguments for executing like run%s\'echo "hello, world!"\'' % (
            global_env['split_function']
        )
    )
    parser.add_argument(
        '--host', dest='hosts',
        nargs='?',
        help='connection strings like user%shost%sport' % (
            global_env['split_user'], global_env['split_port']
        )
    )
    parser.add_argument(
        '-r', dest='run', action='store_true',
        help='execute run() with given arguments'
    )
    parser.add_argument(
        '-s', dest='sudo', action='store_true',
        help='execute sudo() with given arguments'
    )
    parser.add_argument(
        '-n, --non-interactive', dest='non_interactive',
        action='store_true', default=False,
        help='execution without interactive cli'
    )
    parser.add_argument(
        '-p, --parallel', dest='parallel',
        action='store_true', default=False,
        help='parallel execution with or without interactive cli'
    )
    parser.add_argument(
        '--config', dest='config_file',
        help='ini, json or yaml config file for updating global environment'
    )
    return parser.parse_args()


def load_config(config_file=''):
    """Set global variables.

    Hardcode:
      global_env['functions'] = globals()
      global_env['localhost'] = ['localhost', '127.0.0.1', gethostname(),]
      global_env['stdin_queue'] = gevent.queue.Queue()

    Args:
      config_file (str): path to config file

    """
    logging.debug('executing load_config function')
    logging.debug('arguments from cli and another locals: %s', locals())

    # processing config file
    if not os.path.exists(config_file):
        if os.path.exists('factory.ini'):
            config_file = 'factory.ini'
        elif os.path.exists('factory.json'):
            config_file = 'factory.json'
        elif os.path.exists('factory.yaml'):
            config_file = 'factory.yaml'
        else:
            config_file = ''
    logging.debug('config file: %s', config_file)
    if config_file:
        if '.ini' in config_file:
            try:
                from ConfigParser import ConfigParser
            except ImportError:
                from configparser import ConfigParser
            c = ConfigParser()
            try:
                c.read(config_file)
                global_env.update(c.__dict__)
            except:
                logging.error("can't load config from %s", config_file, exc_info=True)
        elif '.json' in config_file:
            try:
                import json
                with open(config_file, 'r') as f:
                    global_env.update(json.load(f))
            except:
                logging.error("can't load config from %s", config_file, exc_info=True)
        elif '.yaml' in config_file:
            try:
                import yaml
                with open(config_file, 'r') as f:
                    global_env.update(yaml.load(f))
            except:
                logging.error("can't load config from %s", config_file, exc_info=True)
        else:
            logging.error("can't determine file format for %s", config_file)

    global_env['functions'] = globals()

    global_env['localhost'] = ['localhost',
                               '127.0.0.1',
                               gethostname(),]

    global_env['stdin_queue'] = gevent.queue.Queue()

    logging.debug('global environment: %s', global_env)


def parse_functions(l_arguments):
    """Convert input list to list of functions with args and kwargs.

    Args:
      l_arguments (list): list of tasks for executing

    Return:
      list: list of tuples of functions with args and kwargs

    Examples:
      >>> load_config()
      >>> parse_functions(
      ...      ["echo 'hello world!'",
      ...      'run', "echo 'hello world!'",
      ...      'run', "echo 'hello world!'", 'use_sudo=True',
      ...      "run:echo 'hello world!',use_sudo=True",
      ...      "run:echo 'hello world!'", 'use_sudo=True']
      ... ) # doctest: +NORMALIZE_WHITESPACE
      [('run', ["echo 'hello world!'"], {}),
      ('run', ["echo 'hello world!'"], {}),
      ('run', ["echo 'hello world!'"], {'use_sudo': 'True'}),
      ('run', ["echo 'hello world!'"], {'use_sudo': 'True'}),
      ('run', ["echo 'hello world!'"], {'use_sudo': 'True'})]

    """
    logging.debug('executing parse_functions function')
    logging.debug('arguments %s', l_arguments)

    functions = []
    tasks = []

    # an implicit execution
    logging.debug('checking first argument')
    zero = l_arguments[0].split(global_env['split_function'])[0]
    if zero not in global_env['functions'].keys():
        logging.warning('can not find function, executing built-in run')
        l_arguments.insert(0, 'run')
        logging.debug('new arguments %s', l_arguments)

    # step 1: split all to lists of functions with args
    logging.debug('spliting all arguments to lists of functions with args')
    for f in l_arguments:
        if f in global_env['functions'].keys():
            functions.append([f])
        elif global_env['split_function'] in f:
            function, args = f.split(global_env['split_function'])
            if function in global_env['functions'].keys():
                functions.append([function])
                functions[-1].extend(args.split(global_env['split_args']))
            else:
                functions[-1].append(f)
        else:
            functions[-1].append(f)
    logging.debug('functions %s', functions)

    # step 2: parse args and kwargs for each function
    logging.debug('parsing args and kwargs for each function')
    for f in functions:
        fnct = f[0]
        args = f[1:]
        kwargs = {}
        for a in args[::-1]:
            e = a.find('=')
            if e != (-1 or 0) and a[e-1] not in global_env['arithmetic_symbols']:
                k, v = a.split('=')
                k = k.strip()
                v = v.strip()
                kwargs[k] = v
                args.pop()
            else:
                break
        tasks.append((fnct, args, kwargs))
    logging.debug('tasks %s', tasks)

    return tasks

def run_tasks_on_host(connect_string, tasks, con_args=''):
    """Open connect to host and executed tasks.

    Use set_connect_env context manager for set connect args.
    Then set check_is_root variable.
    And then executed tasks for this host.

    Args:
      connect_string (str): [user@]host[:port]
      tasks (list): list of tuples of functions with args and kwargs
      con_args (str): options for ssh

    """
    logging.debug('executing run_tasks_on_host function')
    logging.debug('arguments for executing and another locals: %s', locals())
    with set_connect_env(connect_string, con_args):
        #TODO: checking first connection via ssh
        if global_env['parallel']:
            gevent.sleep(0)
            logging.debug('tasks will be processed in parallel')
            threads = [gevent.spawn(global_env['functions'][function], *args, **kwargs) for function, args, kwargs in tasks]
            gevent.joinall(threads)
        else:
            logging.debug('tasks will be processed one by one')
            for function, args, kwargs in tasks:
                global_env['functions'][function](*args, **kwargs)



def stdin_loop():
    """Global loop: wait for sys.stdin and put line from it to global queue."""
    logging.debug('executing stdin_loop function')
    while True:
        try:
            wait_read(sys.stdin.fileno())
        except AttributeError:
            logging.error("can't process sys.stdout", exc_info=True)
            break
        l = sys.stdin.readline()
        logging.debug('message from sys.stdin: %s', l)
        global_env['stdin_queue'].put_nowait(l)


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
        connect_env.check_is_root = check_is_root()
        logging.debug('connect_env: %s', connect_env)
        return connect_env

    def __exit__(self, type, value, traceback):
        """Reinitialized global connect_env as Empty class.

        FIXME: is it really works?! I doesn't think so...

        """
        logging.debug('reinitialization global connect_env as Empty class')
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


if __name__ == '__main__':
    main()

