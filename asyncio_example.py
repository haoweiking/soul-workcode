import time
import asyncio


now = lambda : time.time()


async def do_some_work(x):
    print('Waiting: ', x)

    # 若遇到阻塞 通过await asyncio.sleep 主动挂起协程 让出控制权
    await asyncio.sleep(x)
    return 'Done after {}s'.format(x)


def callback(future):
    print('Callback: ', future.result())


# start = now()
#
# # coroutine = do_some_work(2)
#
# coroutine1 = do_some_work(1)
# coroutine2 = do_some_work(2)
# coroutine3 = do_some_work(4)
#
# tasks = [
#     asyncio.ensure_future(coroutine1),
#     asyncio.ensure_future(coroutine2),
#     asyncio.ensure_future(coroutine3),
# ]
#
# # get_event_loop 创建事件循环
# loop = asyncio.get_event_loop()
#
# # run_until_complete 将协程注册到事件循环，并启动事件循环
# # loop.run_until_complete(coroutine)
#
# # loop.create_task asyncio.ensure_future 均可创建task
# # task = loop.create_task(coroutine)
# # task = asyncio.ensure_future(coroutine)
#
# # task 执行结束时会触发回调函数 callback
# # task.add_done_callback(callback)
#
# # print(task)
# # loop.run_until_complete(task)
# # print(task)
#
# # asyncio.wait 实现并发 也可以使用 asyncio.gather(*tasks)
# loop.run_until_complete(asyncio.wait(tasks))
# for task in tasks:
#     print('Task ret: ', task.result())
#
#
# # print('Task ret: ', task.result())
# print('TIME: ', now() - start)

async def main():
    # 协程嵌套
    coroutine1 = do_some_work(1)
    coroutine2 = do_some_work(2)
    coroutine3 = do_some_work(4)

    tasks = [
        asyncio.ensure_future(coroutine1),
        asyncio.ensure_future(coroutine2),
        asyncio.ensure_future(coroutine3),
    ]
    # dones, pendings = await asyncio.wait(tasks)
    results = await asyncio.gather(*tasks)
    # for task in dones:
    #     print('Task ret: ', task.result())
    for result in results:
        print('Task ret: ', result)


if __name__ == '__main__':
    start = now()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    print('TIME: ', now() - start)
