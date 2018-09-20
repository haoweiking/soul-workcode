import socket
import gevent
from gevent import socket, monkey
from gevent.pool import Pool
import time


monkey.patch_all()

HOST = '127.0.0.1'
PORT = 8080
def socket_client(i):
    s = socket.socket()
    s.connect((HOST, PORT))
    msg = bytes(('This is gevent: %s' % i), encoding='utf8')
    s.sendall(msg)
    data = s.recv(1024)
    print('Received:', data.decode())

    s.close()


def main():
    start_time = time.time()
    pool = Pool(5)
    threads = [pool.spawn(socket_client, i) for i in range(2000)]
    gevent.joinall(threads)
    end_time = time.time()
    print('Total is %s', end_time - start_time)


if __name__ == '__main__':
    main()
