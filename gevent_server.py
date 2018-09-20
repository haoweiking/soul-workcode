import sys
import socket
import time
import gevent
import urllib.request as request
from gevent import socket, monkey, pool
monkey.patch_socket()


def f(n):
    for i in range(n):
        print(gevent.getcurrent(), i)


def main_f():
    g1 = gevent.spawn(f, 5)
    g2 = gevent.spawn(f, 5)
    g3 = gevent.spawn(f, 5)
    g1.join()
    g2.join()
    g3.join()


def foo(url):
    print('GET: %s' % url)
    resp = request.urlopen(url)
    data = resp.read()
    print('%d bytes received from %s.' % (len(data), url))


def main__foo():
    gevent.joinall([gevent.spawn(foo, 'https://www.python.org/'),
                    gevent.spawn(foo, 'https://www.yahoo.com/'),
                    gevent.spawn(foo, 'https://github.com/'),
                    ])


def handle_request(conn):
    try:
        data = conn.recv(1024)
        print('recv:', data)
        data = 'From socketServer:192.168.1.103--%s' % data.decode('utf8')
        conn.sendall(bytes(data, encoding='utf8'))
        if not data:
            conn.shutdown(socket.SHUT_WR)
    except Exception as ex:
        print(ex)
    finally:
        conn.close()


def server(port, pool):
    s = socket.socket()
    s.bind(('127.0.0.1', port))
    s.listen()
    while True:
        cli, addr = s.accept()
        print('wait...')
        pool.spawn(handle_request, cli)


def main():
    pool = gevent.pool.Pool(5)
    server(8080, pool)


if __name__ == '__main__':
    main()
