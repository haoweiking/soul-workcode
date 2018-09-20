import gevent
import urllib.request
from gevent import monkey


monkey.patch_all()


def run_task(url):
    print('visit --> %s' % url)
    try:
        response = urllib.request.urlopen(url)
        data = response.read()
        print('%d bytes received from %s.' % (len(data), url))
    except Exception as e:
        print(e)


def main():
    urls = ['https://www.baidu.com',
            'https://docs.python.org/3/library/urllib.html',
            'https://www.cnblogs.com/wangmo/p/7784867.html',
            'https://www.weibo.com/']
    greenlets = [gevent.spawn(run_task, url) for url in urls]
    gevent.joinall(greenlets)


if __name__ == '__main__':
    main()
