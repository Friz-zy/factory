factory
=======
[![MIT](http://img.shields.io/badge/License-MIT-green.svg)](https://github.com/Friz-zy/factory/blob/master/LICENSE)  [![Python 2.7](http://img.shields.io/badge/Python-2.5--2.7-yellowgreen.svg)](https://www.python.org/)  [![gevent](http://img.shields.io/badge/Based-Gevent-yellow.svg)](https://pypi.python.org/pypi/gevent/1.0.1)

[![Build Status](https://travis-ci.org/Friz-zy/factory.svg?branch=master)](https://travis-ci.org/Friz-zy/factory) [![Coverage Status](https://img.shields.io/coveralls/Friz-zy/factory.svg)](https://coveralls.io/r/Friz-zy/factory)

Factory is proof-of-concept realization of [fabric](https://github.com/fabric/fabric) with a number of differences:
* run() function works in the same way with subprocess.popen under localhost as under ssh connect to remote host
* Factory uses openssh or any another ssh client (you should modified config for this), so you can use all power of ssh sockets
* Factory uses [gevent](https://github.com/surfly/gevent) library for asynchronous executing

Examples:

* Using build in functions
```bash
fact run 'echo "hello, world!"'
frizzy@localhost in: echo "hello, world!"
frizzy@localhost out: hello, world!
```

* Using factfile
```bash
cat factfile
#!/usr/bin/env python
# coding=utf-8
from factory.api import run

def hello_fact():
    run('echo "this if factfile"')
```

```bash
fact hello_fact
frizzy@localhost in: echo "this if factfile"
frizzy@localhost out: this if factfile
```

* Using fabfile
```bash
cat fabfile 
#!/usr/bin/env python
# coding=utf-8
from fabric.api import run

def hello_fab():
    run('echo "this if fabfile"')
```

```bash
fact hello_fab
frizzy@localhost in: echo "this if fabfile"
frizzy@localhost out: this if fabfile
```

* And even this
```bash
cat my_little_script.py 
#!/usr/bin/env python
# coding=utf-8
from factory.api import *

def hello():
    run('echo "hello world!"')

if __name__ == '__main__':
    # running hello on two hosts
    env.hosts = ['localhost', 'test@127.0.0.1']
    for host in env.hosts:
        with set_connect_env(host):
            hello()
            run(raw_input('type the command: '))
```

```bash
python my_little_script.py 
frizzy@localhost in: echo "hello world!"
frizzy@localhost out: hello world!
type the command: echo "hello, username!"
frizzy@localhost in: echo "hello, username!"
frizzy@localhost out: hello, username!
test@127.0.0.1 in: echo "hello world!"
test@127.0.0.1 out: hello world!
type the command: echo "hello, test"             
test@127.0.0.1 in: echo "hello, test"
test@127.0.0.1 out: hello, test
```

[WiKi](https://github.com/Friz-zy/factory/wiki) will be soon

[Board](https://trello.com/b/TNRr7EbW/factory) on [trello](https://trello.com)

[Filipp Kucheryavy aka Frizzy](mailto:filipp.s.frizzy@gmail.com)
