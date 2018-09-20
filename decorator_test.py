#!/usr/bin/env python
#coding:utf-8
# Author: Ocean <yousangdandan@yeah.net>
# Created Time: 四  9/20 11:32:17 2018

from functools import wraps


def sum_add(*args1):
    def decorator(func):
        @wraps(func)
        def my_sum(*args2):
            my_s = 0
            for n in args1:
                my_s = my_s + n
            return func(*args2) + my_s
        return my_sum
    return decorator


@sum_add(10, 20)
def sum(*args):
    s = 0
    for n in args:
        s = s + n
    return s


print(sum(1,2,3,4,5))
print(sum.__name__)
