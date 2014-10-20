#!/usr/bin/env python
# coding=utf-8
"""Tasks executing via ssh and sh.

Factory provides api for local and nonlocal running of functions,scripts, etc via ssh and sh.
It is proof-of-concept realization of [fabric](https://github.com/fabric/fabric) with a number of differences:
* run() function works in the same way with subprocess.popen under localhost as under ssh connect to remote host
* Factory uses openssh or any another ssh client (you should modified config for this), so you can use all power of ssh sockets
* Factory uses [gevent](https://github.com/surfly/gevent) library for asynchronous executing

Example:
  $ main.py 'echo "hello, world!"'
  $ main.py --host user@host:port run:'uname -a'

Config files:
  Factory uses standart python logging module,
    so you can set your own config via config file:
      logging.ini, logging.json or logging.yaml
    hardcode logging config:
      format=u'%(asctime)s  %(name)s\t%(levelname)-8s\t%(message)s',
      datefmt='%d %b %Y %H:%M:%S',
      stream=sys.stdout, # will be replacing by filename
      filename= 'factory.log',
      filemode='a',
      level=logging.INFO,

  You can update envs.common dict via config file:
    always load if exist: factory.ini or factory.json or factory.yaml
    and --config PATH cli option

  Load factfile:
    always load if exist: factfile.py or factfile
    and --factfile PATH cli option

  Load fabfile:
    always load if exist: fabfile.py or fabfile
    and --fabfile PATH cli option

"""

# This file is part of https://github.com/Friz-zy/factory

from __future__ import with_statement
import os
import sys

major, minor, micro, releaselevel, serial = sys.version_info
if (major,minor) < (2,5):
    print 'Sorry, but factory requires python 2.5 or highest. Bye!'
    sys.exit(2)

import imp
import logging
import argparse
from copy import copy

import gevent
from gevent.socket import wait_read
from state import envs, stdin_queue


logging.basicConfig(
    format=u'%(asctime)s  %(name)s\t%(levelname)-8s\t%(message)s',
    datefmt='%d %b %Y %H:%M:%S',
    stream=sys.stdout, # will be replacing by filename
    filename= 'factory.log',
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


def main():
    logging.debug('executing main function')
    logging.debug('arguments from cli and another locals: %s', locals())
    # load build in operations
    import operations
    for key, value in operations.__dict__.iteritems():
        if callable(value):
            envs.common.functions[key] = value
    load_config()
    load_factfile()
    load_fabfile()
    args = parse_cli()
    if args.config_file:
        load_config(args.config_file)
    if args.factfile:
        load_factfile(args.factfile)
    if args.fabfile:
        load_fabfile(args.fabfile)
    if args.hosts:
        envs.common.hosts = args.hosts.split(envs.common.split_hosts)
    # --user
    if args.user:
        envs.common.user = args.user
    # --port
    if args.port:
        envs.common.ssh_port = args.port
    # --show-errors
    if args.show_errors:
        envs.common.show_errors = args.show_errors
    # -r -s shortcuts
    if args.sudo:
        args.command.insert(0, 'sudo')
    elif args.run:
        args.command.insert(0, 'run')

    # update globals interactive and parallel from cli
    logging.debug('updating globals interactive and parallel from cli')
    envs.common.interactive = not args.non_interactive
    envs.common.parallel = args.parallel

    functions_to_execute = parse_functions(args.command)

    logging.debug('arguments from cli and another locals before real executing of tasks: %s', locals())

    # start of stdin loop
    if envs.common.interactive:
        logging.debug('starting global stdin loop')
        sloop = gevent.spawn(stdin_loop)

    if not envs.common.parallel:
        logging.debug('hosts will be processed one by one')
        for host in envs.common.hosts:
            logging.debug('host %s, functions %s', host, functions_to_execute)
            run_tasks_on_host(host, functions_to_execute, copy(envs.common), copy(envs.connect))
    else:
        threads = []
        logging.debug('hosts will be processed in parallel')

        for host in envs.common.hosts:
            logging.debug('host %s, functions %s', host, functions_to_execute)
            # args and kwargs for run_tasks_on_host()
            args = (host, functions_to_execute, copy(envs.common), copy(envs.connect))
            kwargs = {}
            threads.append(gevent.spawn(run_tasks_on_host, *args, **kwargs))
        gevent.joinall(threads)

    # finish stdin loop
    if envs.common.interactive:
        logging.debug('finishing global stdin loop')
        sloop.kill()


def load_config(config_file=''):
    """Set global variables.

    Check config_file path:
      factory.ini or factory.json or factory.yaml
      and --config PATH cli option

    Args:
      config_file (str): path to config file

    """
    logging.debug('executing load_config function')
    logging.debug('arguments from cli and another locals: %s', locals())

    # processing config file
    for filename in (config_file, 'factory.ini', 'factory.json', 'factory.yaml'):
        if os.path.exists(filename):
            config_file = filename
            break
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
                envs.common.update(c.__dict__)
            except:
                logging.error("can't load config from %s", config_file, exc_info=True)
        elif '.json' in config_file:
            try:
                import json
                with open(config_file, 'r') as f:
                    envs.common.update(json.load(f))
            except:
                logging.error("can't load config from %s", config_file, exc_info=True)
        elif '.yaml' in config_file:
            try:
                import yaml
                with open(config_file, 'r') as f:
                    envs.common.update(yaml.load(f))
            except:
                logging.error("can't load config from %s", config_file, exc_info=True)
        else:
            logging.error("can't determine file format for %s", config_file)

    logging.debug('global environment: %s', envs.common)


def load_factfile(factfile=''):
    """Load factfile.

    Check factfile path:
      factfile.py or factfile
      and --config PATH cli option

    Args:
      factfile (str): path to factfile

    """
    logging.debug('executing load_factfile function')
    logging.debug('arguments from cli and another locals: %s', locals())

    # processing factfile
    for filename in (factfile, 'factfile.py', 'factfile'):
        if os.path.exists(filename):
            factfile = filename
            break
    logging.debug('factfile: %s', factfile)
    if factfile:
        factfile = imp.load_source('factfile', factfile)
        for key, value in factfile.__dict__.iteritems():
            if callable(value):
                envs.common.functions[key] = value

    logging.debug('global environment: %s', envs.common)


def load_fabfile(fabfile=''):
    """Load fabfile.

    Check fabfile path:
      fabfile.py or fabfile
      and --config PATH cli option

    Args:
      fabfile (str): path to fabfile

    """
    logging.debug('executing load_fabfile function')
    logging.debug('arguments from cli and another locals: %s', locals())

    # processing fabfile
    for filename in (fabfile, 'fabfile.py', 'fabfile'):
        if os.path.exists(filename):
            fabfile = filename
            break
    logging.debug('fabfile: %s', fabfile)
    if fabfile:
        import tempfile
        with open(fabfile, 'r') as fab:
            src = fab.read().replace('fabric', 'factory')
            temp = tempfile.NamedTemporaryFile()
            temp.write(src)
            temp.flush()
            fabfile = imp.load_source('fabfile', temp.name)
            temp.close()
        for key, value in fabfile.__dict__.iteritems():
            if callable(value):
                envs.common.functions[key] = value

    logging.debug('global environment: %s', envs.common)



def parse_cli():
    """Use argparse for command line.

    Convert the strings to objects and assign them as attributes of the namespace.

    Return:
      namespace: like Namespace(foo='FOO', x=None)

    """
    logging.debug('parsing %s', sys.argv)
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        prog='fact',
        description='Tasks executing via ssh and sh',
    )
    parser.add_argument(
        'command', nargs='+',
        help="""An commands with arguments for executing like:
  command arg1 arg2
  command{0}arg1{1}arg2
  command1 arg1 arg2 command2 arg1 arg2
  command1{0}arg1{1}arg2 command2{0}arg1{1}arg2
Examples:
  'echo "hello world!"'
  run 'echo "hello world!"'
  run 'echo "hello world!"' use_sudo=True
  'run{0}echo "hello world!"{1}use_sudo=True'
  'run{0}echo "hello world!"' use_sudo=True
Warning: don't use command arg1{1}arg2 format""".format(
            envs.common.split_function,
            envs.common.split_args,
        )
    )
    parser.add_argument(
        '-H', '--host', dest='hosts',
        nargs='?',
        help='''connection strings like user%shost%sport
  default is %s''' % (
            envs.common.split_user,
            envs.common.split_port,
            envs.common.hosts
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
        '-n', '--non-interactive',
        dest='non_interactive',
        action='store_true', default=False,
        help='execution without interactive cli'
    )
    parser.add_argument(
        '-p', '--parallel', dest='parallel',
        action='store_true', default=False,
        help='''parallel execution with or without
  interactive cli'''
    )
    parser.add_argument(
        '--config', dest='config_file',
        help='''ini, json or yaml config file
  for updating global environment'''
    )
    parser.add_argument(
        '--factfile', dest='factfile',
        help='path to factfile'
    )
    parser.add_argument(
        '--fabfile', dest='fabfile',
        help='path to fabfile'
    )
    parser.add_argument(
        '--user', dest='user',
        help='''username for ssh login,
  default is %s''' % envs.common.user
    )
    parser.add_argument(
        '--port', dest='port',
        help='''ssh port for connections,
  default is 22'''
    )
    parser.add_argument(
        '--show-errors', dest='show_errors',
        action='store_true', default=False,
        help='''show fact warnings and errors in or not in
  interactive mode, default is False'''
    )
    return parser.parse_args()


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
    zero = l_arguments[0].split(envs.common.split_function)[0]
    if zero not in envs.common.functions.keys():
        logging.warning('can not find function, executing built-in run')
        l_arguments.insert(0, 'run')
        logging.debug('new arguments %s', l_arguments)

    # step 1: split all to lists of functions with args
    logging.debug('spliting all arguments to lists of functions with args')
    for f in l_arguments:
        if f in envs.common.functions.keys():
            functions.append([f])
        elif envs.common.split_function in f:
            function, args = f.split(envs.common.split_function)
            if function in envs.common.functions.keys():
                functions.append([function])
                functions[-1].extend(args.split(envs.common.split_args))
            else:
                functions[-1].append(f)
        else:
            # NOTE: functions[-1].extend(args.split(envs.common.split_args))
            # don't uses in this case
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
            if e != (-1 or 0) and a[e-1] not in envs.common.arithmetic_symbols:
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

def run_tasks_on_host(connect_string, tasks, common_env, connect_env, con_args=''):
    """Set greenlet envs, open connect to host and executed tasks.

    Use set_connect_env context manager for set connect args.
    And then executed tasks for this host.
    Hack for greenlets:
      common_env its copy of envs.common
      connect_env its copy of envs.connect

    Args:
      connect_string (str): [user@]host[:port]
      tasks (list): list of tuples of functions with args and kwargs
      common_env (AttributedDict class object): global class instance for global options
      connect_env (AttributedDict class object): global class instance for connect environment
      con_args (str): options for ssh

    """
    envs.common = common_env
    envs.connect = connect_env
    logging.debug('executing run_tasks_on_host function')
    logging.debug('arguments for executing and another locals: %s', locals())
    from context_managers import set_connect_env
    with set_connect_env(connect_string, con_args):
        #TODO: checking first connection via ssh
        if envs.common.parallel:
            gevent.sleep(0)
            logging.debug('tasks will be processed in parallel')
            threads = []
            for function, args, kwargs in tasks:
                args = (function, args, kwargs,
                        copy(envs.common),
                        copy(envs.connect)
                )
                threads.append(gevent.spawn(run_task, *args))
            gevent.joinall(threads)
        else:
            logging.debug('tasks will be processed one by one')
            for function, args, kwargs in tasks:
                run_task(function, args, kwargs, copy(envs.common), copy(envs.connect))



def run_task(function, args, kwargs, common_env, connect_env):
    """Set greenlet envs and run task.

    Hack for greenlets:
      common_env its copy of envs.common
      connect_env its copy of envs.connect

    Args:
      function (str): name of function from envs.common.functions dict
        that will be executed as task
      args (tuple): args for executed task
      kwargs(dict): kwargs for executed task
      common_env (AttributedDict class object): global class instance for global options
      connect_env (AttributedDict class object): global class instance for connect environment

    """
    envs.common = common_env
    envs.connect = connect_env
    envs.common.functions[function](*args, **kwargs)


def stdin_loop():
    """Global loop: wait for sys.stdin and put line from it to global queue."""
    logging.debug('executing stdin_loop function')
    win = os.name == 'nt'
    while True:
        try:
            # wait_read doesn't work on windows
            if win:
                from gevent import monkey
                monkey.patch_sys()
                l = sys.stdin.readline()
            else:
                wait_read(sys.stdin.fileno())
                l = sys.stdin.readline()
            logging.debug('message from sys.stdin: %s', l)
            stdin_queue.put_nowait(l)
        except AttributeError:
            logging.error("can't process sys.stdout", exc_info=True)
            break


if __name__ == '__main__':
    main()

