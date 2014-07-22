#!/usr/bin/env python
# coding=utf-8
"""Factory provides api for local and nonlocal running of functions,scripts, etc via shh and *sh."""
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

import gevent
from gevent.subprocess import Popen, PIPE
from gevent.local import local

# default variables
global_env = {'interactive': True,
              'functions': {},
              'localhost': [],
              'split_function': ':',
              'split_args': ',,',
              'split_hosts': ',',
              'split_user': '@',
              'split_port': ':',
              'default_shell': 'sh',
              'ssh_binary': 'ssh',
              'ssh_port': 22,}

connect_env = local()


def run(command, use_sudo=False, user='', group='', freturn=False):
    """
    """
    logger = connect_env.logger
    interactive = global_env['interactive']
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
        end = ''
    else:
        scommand = [global_env['ssh_binary'],
                            '-p',
                            str(connect_env.port),
                            ''.join((connect_env.user,
                                    '@',
                                    connect_env.host)),
                            connect_env.con_args]
        p = Popen(scommand, stdout=PIPE, stderr=PIPE, stdin=PIPE)
        if not p.stderr.readline():
            end = p.stdout.readline().rstrip()[-1][-1]
            p.stdin.writeline(command)
            p.stdin.flash()
        else:
            pass
    # run another command
    if not interactive:
        gevent.sleep(0)
    # processing std loop
    sout = ' '
    sumout = ''
    sumerr = ''
    #TODO: checking popen status of execution
    while sout:
        serr = p.stderr.readline()
        if serr:
            sumerr += serr
            logger.info('err: %s', serr)
            if interactive:
                sys.stderr.write('%s err: %s' % (connect_env.connect_string, serr))
                sys.stderr.flush()
        sout = p.stdout.readline()
        if sout:
            if end and sout.readline().rstrip()[-1][-1] == end:
                break
            sumout += sout
            logger.info('out: %s', sout)
            #TODO: y\n; password
            if interactive:
                sys.stdout.write('%s out: %s' % (connect_env.connect_string, sout))
                sys.stderr.flush()
        if not interactive:
            gevent.sleep(0)
    #TODO: popen return code
    #status = p.status()
    status = 0
    p.kill()
    if freturn:
        return (sumout, sumerr, status)
    return sumout
                
            


def sudo(command, user='', group='', freturn=False):
    """sudo is alias for run(use_sudo=True)"""
    return run(command, use_sudo=True, user=user, group=group, freturn=freturn)


def check_is_root():
    out, err, status = run('id -u', freturn=True)
    if not status:
        return not int(out)
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('function',
                    help='an function for executing like run%s\'echo "hello, world!"\'' % global_env['split_function'])
    parser.add_argument('--host', dest='hosts',
                    help='conectin strings like user%shost%sport' % (global_env['split_user'], global_env['split_port']))

    global_env['functions'] = globals()
    logging.basicConfig(format=u'%(asctime)s  %(name)s\t[%(levelname)-8s]\t%(message)s',
                        datefmt='%d %b %Y %H:%M:%S',
                        stream=sys.stdout, # will be replacing by filename
                        filename= __file__.replace('.py', '.log'), # save log as ./factory.log
                        filemode='a',
                        level=logging.INFO)

    global_env['localhost'] = ['localhost',
                               '127.0.0.1',
                               gethostname(),]

    args = parser.parse_args()
    # by default run command at localhost
    if not args.hosts:
        hosts = ['localhost']
    else:
        hosts = args.hosts.split(global_env['split_hosts'])
    function, fargs = args.function.split(global_env['split_function'])
    #TODO: find right way to split args
    fargs = fargs.split(global_env['split_args'])
    
    if global_env['interactive']:
        for host in hosts:
            run_tasks_on_host(host, {function: fargs})

def run_tasks_on_host(connect_string, tasks, con_args=''):
    """
    """
    connect_env.connect_string = connect_string
    if global_env['split_user'] in connect_string:
        connect_env.user, connect_string = connect_string.split(global_env['split_user'])
    else:
        connect_env.user = getuser()
    if global_env['split_port'] in connect_string:
        connect_env.host, connect_env.port = connect_string.split(global_env['split_port'])
    else:
        connect_env.host = connect_string
        connect_env.port = global_env['ssh_port']
    connect_env.con_args = con_args
    connect_env.logger = logging.getLogger(''.join((connect_env.user,
                                                    global_env['split_user'],
                                                    connect_env.host)))
    #TODO: checking first connection via ssh
    connect_env.check_is_root = check_is_root()
    # if uses greenlets
    #if not global_env['interactive']:
    #    gevent.sleep(0)
    
    for function in tasks.keys():
        global_env['functions'][function](tasks[function])
    
    #TODO: find way to import globals in gevent.spawn tread
    #threads = [gevent.spawn(global_env['functions'][function], tasks[function]) for function in tasks.keys()]
    #gevent.joinall(threads)
    
    
if __name__ == '__main__':
    main()

