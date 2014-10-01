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

  You can update global_env dict via config file:
    factory.ini, factory.json or factory.yaml
    or --config PATH cli option

"""

# This file is part of https://github.com/Friz-zy/factory

from __future__ import with_statement
import os
import sys

major, minor, micro, releaselevel, serial = sys.version_info
if (major,minor) < (2,5):
    print 'Sorry, but factory requires python 2.5 or highest. Bye!'
    sys.exit(2)

import logging
import argparse

import gevent
import gevent.queue
from gevent.socket import wait_read
from state import global_env, connect_env


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
    args = parse_cli()
    if args.config_file:
        load_config(args.config_file)
    else:
        load_config()
    logging.debug('executing main function')
    logging.debug('arguments from cli and another locals: %s', locals())
    if args.hosts:
        global_env.hosts = args.hosts.split(global_env.split_hosts)
    # -r -s shortcuts
    if args.sudo:
        args.function.insert(0, 'sudo')
    elif args.run:
        args.function.insert(0, 'run')

    # update globals interactive and parallel from cli
    logging.debug('updating globals interactive and parallel from cli')
    global_env.interactive = not args.non_interactive
    global_env.parallel = args.parallel

    functions_to_execute = parse_functions(args.function)

    # start of stdin loop
    if global_env.interactive:
        logging.debug('starting global stdin loop')
        sloop = gevent.spawn(stdin_loop)

    if not global_env.parallel:
        logging.debug('hosts will be processed one by one')
        for host in global_env.hosts:
            logging.debug('host %s, functions %s', host, functions_to_execute)
            run_tasks_on_host(host, functions_to_execute)
    else:
        threads = []
        logging.debug('hosts will be processed in parallel')
        for host in global_env.hosts:
            logging.debug('host %s, functions %s', host, functions_to_execute)
            args = (host, functions_to_execute)
            kwargs = {}
            threads.append(gevent.spawn(run_tasks_on_host, *args, **kwargs))
        gevent.joinall(threads)

    # finish stdin loop
    if global_env.interactive:
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
            global_env.split_function
        )
    )
    parser.add_argument(
        '-H, --host', dest='hosts',
        nargs='?',
        help='connection strings like user%shost%sport' % (
            global_env.split_user, global_env.split_port
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
        '-n', '--non-interactive', dest='non_interactive',
        action='store_true', default=False,
        help='execution without interactive cli'
    )
    parser.add_argument(
        '-p', '--parallel', dest='parallel',
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
      global_env['functions'] = operations.__dict__
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

    # load build in operations
    import operations
    for key, value in operations.__dict__.iteritems():
        if hasattr(value, '__call__'):
            global_env.functions[key] = value

    global_env.stdin_queue = gevent.queue.Queue()

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
    zero = l_arguments[0].split(global_env.split_function)[0]
    if zero not in global_env.functions.keys():
        logging.warning('can not find function, executing built-in run')
        l_arguments.insert(0, 'run')
        logging.debug('new arguments %s', l_arguments)

    # step 1: split all to lists of functions with args
    logging.debug('spliting all arguments to lists of functions with args')
    for f in l_arguments:
        if f in global_env.functions.keys():
            functions.append([f])
        elif global_env.split_function in f:
            function, args = f.split(global_env.split_function)
            if function in global_env.functions.keys():
                functions.append([function])
                functions[-1].extend(args.split(global_env.split_args))
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
            if e != (-1 or 0) and a[e-1] not in global_env.arithmetic_symbols:
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
    from context_managers import set_connect_env
    with set_connect_env(connect_string, con_args):
        #TODO: checking first connection via ssh
        if global_env.parallel:
            gevent.sleep(0)
            logging.debug('tasks will be processed in parallel')
            threads = [gevent.spawn(global_env.functions[function], *args, **kwargs) for function, args, kwargs in tasks]
            gevent.joinall(threads)
        else:
            logging.debug('tasks will be processed one by one')
            for function, args, kwargs in tasks:
                global_env.functions[function](*args, **kwargs)



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
        global_env.stdin_queue.put_nowait(l)

if __name__ == '__main__':
    main()

