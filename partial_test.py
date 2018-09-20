#!/usr/bin/env python
#coding:utf-8
# Author: Ocean <yousangdandan@yeah.net>
# Created Time: 四  9/20 11:48:16 2018

from functools import partial


#def sum(*args, **others):
#    s = 0
#    for n in args:
#        s = s + n
#    s1 = 0
#    for k in others:
#        s1 = s1 + others[k]
#    return s + s1

#D = {'value1':10, 'value2':20}

#print(sum(1, 2, 3, 4, 5, **D))

def sum(*args):
    s = 0
    for n in args:
        s = s + n
    return s


sum_add_10 = partial(sum, 10)
sum_add_10_20 = partial(sum, 10, 20)
print('A______________ sum id: ')
print(sum)
print('B______________ partial id: ')
print(partial(sum, 10))
print(sum_add_10(1,2,3,4,5))
print(sum_add_10_20(1,2,3,4,5))


L = list(range(1, 11))
slice_5_10 = partial(slice, 5, 10)
print(L[slice_5_10()])


def mod(m, *, key=2):
    return m % key == 0


mod_to_2 = partial(mod, key=2)
print('A__3__basic func: ')
print(mod(3))
print('B__3__partial func: ')
print(mod_to_2(3))
mod_to_5 = partial(mod, key=5)
print('C__25__basic func: ')
print(mod(25, key=5))
print('D__25__partial func: ')
print(mod_to_5(25))
