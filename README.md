factory
=======

Factory is proof-of-concept realization of [fabric](https://github.com/fabric/fabric) with a number of differences:
* run() function works in the same way with subprocess.popen under localhost as under ssh connect to remote host
* Factory uses openssh or any another ssh client (you should modified config for this), so you can use all power of ssh sockets
* Factory uses [gevent](https://github.com/surfly/gevent) library for asynchronous executing
