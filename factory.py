#!/usr/bin/env python
# coding=utf-8
"""Tasks executing via ssh and sh.

Factory provides api for local and nonlocal running of functions,scripts, etc via ssh and sh.

"""
from __future__ import with_statement
"""
Copyright (c) by Filipp Kucheryavy aka Frizzy <filipp.s.frizzy@gmail.com>
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted 
provided that the following conditions are met:

a. Redistributions of source code must retain the above copyright notice, this list of 
conditions and the following disclaimer. 

b. Redistributions in binary form must reproduce the above copyright notice, this list of 
conditions and the following disclaimer in the documentation and/or other materials provided 
with the distribution. 

c. Neither the name of the nor the names of its contributors may be used to endorse or promote 
products derived from this software without specific prior written permission. 

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS 
OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY 
AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE 
COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, 
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF 
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER 
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF 
ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
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
from socket import gethostname
from getpass import getuser
import logging
import argparse

major, minor, micro, releaselevel, serial = sys.version_info
if (major,minor) < (2,5):
    # provide advice on getting version 2.5 or higher.
    sys.exit(2)

import gevent
import gevent.queue
from gevent.socket import wait_read
from gevent.subprocess import Popen, PIPE

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
              'stdin_queue': None,}

class Empty():
    def __init__(self):
        pass

connect_env = Empty()


def run(command, use_sudo=False, user='', group='', freturn=False):
    """Execute command on host via ssh or subprocess.

    Args:
      command (str): command for executing
      use_sudo (bool): running with sudo prefix if True and current user not root
      user (str): username for sudo -u prefix
      group (str): group for sudo -g prefix
      freturn (bool): return tuple if True, else return str

    Return:
      str if freturn is False: string that contained all stdout messages
      tuple if freturn is True:
        string that contained all stdout messages
        string that contained all stderr
        int that mean return code of command

    """
    logger = connect_env.logger
    interactive = global_env['interactive']
    host_string = ''.join((connect_env.user,
                           '@',
                           connect_env.host))
    # run as root
    if use_sudo:
        if not connect_env.run_as_root:
            if 'sudo' not in command.split():
                command = " ".join(('sudo', command))
    # switching user
    if user:
        if 'sudo' not in command.split():
            command = " ".join(('sudo -u %s -s' % user, command))
        else:
            command.replace('sudo', 'sudo -u %s -s' % user)
    # switching group
    if group:
        if 'sudo' not in command.split():
            command = " ".join(('sudo -g %s -s' % group, command))
        else:
            command.replace('sudo', 'sudo -g %s -s' % group)
    # open new connect
    if connect_env.host in global_env['localhost']:
        p = Popen(command, stdout=PIPE, stderr=PIPE, stdin=PIPE, shell=True)
    else:
        scommand = [global_env['ssh_binary'],
                            '-p',
                            str(connect_env.port),
                            host_string,
                            connect_env.con_args,
                            command]
        p = Popen(scommand, stdout=PIPE, stderr=PIPE, stdin=PIPE)
    # run another command
    if not interactive:
        gevent.sleep(0)
    # processing std loop
    threads = []
    if interactive:
        args = (p, logger, host_string)
        gin = gevent.spawn(in_loop, *args)
        threads.append(gin)

    args = (p, logger, interactive, host_string)
    gout = gevent.spawn(out_loop, *args)
    threads.append(gout)

    args = (p, logger, interactive, host_string)
    gerr = gevent.spawn(err_loop, *args)
    threads.append(gerr)

    gevent.joinall(threads)
    #TODO: check returncode if returncode==None
    sumout = gout.value
    sumerr = gerr.value
    status = p.returncode
    if p.poll() is None:
        p.terminate()
        p.kill()
    if freturn:
        return (sumout, sumerr, status)
    return sumout


def out_loop(p, logger, interactive, host_string):
    """Loop for command stdout.

    Check executing command stdout and put messages to log and sys.stdout.

    Args:
      p (Popen object): executing command
      logger (logging.logger object): command logger instance
      interactive (bool): True if interactive mode, else False
      host_string (str): string for processing sys.stdout

    Return:
      str: string that contained all stdout messages

    """
    sout = ' '
    sumout = ''
    while sout or p.poll() is None:
        sout = p.stdout.readline()
        if sout:
            sumout += sout
            logger.info('out: %s', sout)
            #TODO: y\n; password
            if interactive:
                sys.stdout.write('%s out: %s' % (host_string, sout))
                sys.stdout.flush()
    return sumout


def err_loop(p, logger, interactive, host_string):
    """Loop for command stderr.

    Check executing command stderr and put messages to log and sys.stderr.

    Args:
      p (Popen object): executing command
      logger (logging.logger object): command logger instance
      interactive (bool): True if interactive mode, else False
      host_string (str): string for processing sys.stderr

    Return:
      str: string that contained all stderr messages

    """
    serr = ' '
    sumerr = ''
    while serr or p.poll() is None:
        serr = p.stderr.readline()
        if serr:
            sumerr += serr
            logger.info('err: %s', serr)
            if interactive:
                sys.stderr.write('%s err: %s' % (host_string, serr))
                sys.stderr.flush()
    return sumerr


def in_loop(p, logger, host_string):
    """Loop for command stdin.

    Check global stdin queue and put lines from it to command stdin.

    Args:
      p (Popen object): executing command
      logger (logging.logger object): command logger instance (currently not used)
      host_string (str): string for processing sys.stdout (currently not used)

    """
    lin = 0
    while p.poll() is None:
        if global_env['stdin_queue'].qsize() > lin:
            queue = global_env['stdin_queue'].copy()
            qs = queue.qsize()
            for i, l in enumerate(queue):
                if i >= lin:
                    # TODO: crossystem end of line \n \r \nr
                    p.stdin.write(l)
                    p.stdin.flush()
                if queue.qsize() == 0:
                    break
            lin = qs
        gevent.sleep(0)

def sudo(command, user='', group='', freturn=False):
    """sudo is alias for run(use_sudo=True)

    Args:
      command (str): command for executing
      user (str): username for sudo -u prefix
      group (str): group for sudo -g prefix
      freturn (bool): return tuple if True, else return str

    Return:
      str if freturn is False: string that contained all stdout messages
      tuple if freturn is True:
        string that contained all stdout messages
        string that contained all stderr
        int that mean return code of command

    """
    return run(command, use_sudo=True, user=user, group=group, freturn=freturn)


def check_is_root():
    """Check uid via running id -u command.

    Return:
      bool: True if current user uid is 0, else False

    """
    out, err, status = run('id -u', freturn=True)
    if not status:
        return not int(out)
    return False


def push(src, dst):
    """"""
    pass


def pull(src, dst):
    """"""
    pass


def main():
    load_config()
    args = parse_cli()
    hosts = args.hosts.split(global_env['split_hosts'])
    # -r -s shortcuts
    if args.sudo:
        args.function.insert(0, 'sudo')
    elif args.run:
        args.function.insert(0, 'run')
    # interactive
    global_env['interactive'] = not args.non_interactive
    functions_to_execute = parse_functions(args.function)

    # start of stdin loop
    if global_env['interactive']:
        sloop = gevent.spawn(stdin_loop)

    if global_env['interactive'] and not global_env['parallel']:
        for host in hosts:
            run_tasks_on_host(host, functions_to_execute)
    else:
        threads = []
        for host in hosts:
            args = (host, functions_to_execute)
            kwargs = {}
            threads.append(gevent.spawn(run_tasks_on_host, *args, **kwargs))
        gevent.joinall(threads)

    # finish stdin loop
    if global_env['interactive']:
        sloop.kill()


def parse_cli():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        'function', nargs='+',
        help='an function with arguments for executing like run%s\'echo "hello, world!"\'' % (
            global_env['split_function']
        )
    )
    parser.add_argument(
        '--host', dest='hosts',
        nargs='?', default='localhost',
        help='conectin strings like user%shost%sport' % (
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
        help='parallel execution without interactive cli'
    )
    return parser.parse_args()


def load_config():
    global_env['functions'] = globals()
    
    # TODO: unicode for logging
    logging.basicConfig(
        format=u'%(asctime)s  %(name)s\t[%(levelname)-8s]\t%(message)s',
        datefmt='%d %b %Y %H:%M:%S',
        stream=sys.stdout, # will be replacing by filename
        filename= __file__.replace('.py', '.log'), # save log as ./factory.log
        filemode='a',
        level=logging.INFO
    )

    global_env['localhost'] = ['localhost',
                               '127.0.0.1',
                               gethostname(),]

    global_env['stdin_queue'] = gevent.queue.Queue()


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
    functions = []
    tasks = []

    # an implicit execution
    zero = l_arguments[0].split(global_env['split_function'])[0]
    if zero not in global_env['functions'].keys():
        logging.warning('Can not find function, executing built-in run()')
        l_arguments.insert(0, 'run')

    # step 1: split all to lists of function with args
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

    # step 2: parse args and kwargs for each function
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

    return tasks

def run_tasks_on_host(connect_string, tasks, con_args=''):
    """
    """
    with set_connect_env(connect_string, con_args) as connect_env:
        #TODO: checking first connection via ssh
        connect_env.check_is_root = check_is_root()
        if not global_env['interactive']:
            gevent.sleep(0)
        threads = [gevent.spawn(global_env['functions'][function], *args, **kwargs) for function, args, kwargs in tasks]
        gevent.joinall(threads)


def stdin_loop():
    """Global loop: wait for sys.stdin and put line from it to global queue."""
    while True:
        wait_read(sys.stdin.fileno())
        l = sys.stdin.readline()
        global_env['stdin_queue'].put_nowait(l)


class set_connect_env():
    """Context manager that set connect_env atributes.

    Connect_env attibutes:
      connect_string (str): [user@]host[:port]
      user (str): username for connect
      host (str): hostname or ip for connect
      port (str): port for connect
      con_args (str): options for ssh
      logger (logging.logger object): logger object for this connect

    Examples:
      >>> load_config()
      >>> with set_connect_env('user@host:port', '') as connect_env:
      ...     connect_env.__dict__ # doctest: +NORMALIZE_WHITESPACE
      {'connect_string': 'user@host:port',
      'con_args': '',
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
        self.cs = connect_string
        self.ca = con_args

    def __enter__(self):
        """Set atributes to connect_env object.

        Returns:
          connect_env object with most of all atributes

        """
        connect_string = self.cs
        con_args = self.ca
        connect_env.connect_string = connect_string
        if global_env['split_user'] in connect_string:
            connect_env.user, connect_string = connect_string.split(
                global_env['split_user']
            )
        else:
            connect_env.user = getuser()
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
        return connect_env

    def __exit__(self, type, value, traceback):
        """Reinitialized global connect_env as Empty class.

        FIXME: is it really works?! I doesn't think so...

        """
        connect_env = Empty()


if __name__ == '__main__':
    main()

