# -*- coding: UTF-8 -*-

# 1 有 1、2、3、4 个数字，能组成多少个互不相同且无重复数字的三位数?都是多少?
def fun1():
	for i in range(1, 5):
		for j in range(1, 5):
			for k in range(1, 5):
				if (i != k) and (i != j) and (j != k):
					print i, j, k


'''
2 企业发放的奖金根据利润提成。利润(I)低于或等于 10 万元时，奖金可提 10%;利 润高
于 10 万元，低于 20 万元时，低于 10 万元的部分按 10%提成，高于 10 万元的部分， 可可提
成 7.5%;20 万到 40 万之间时，高于 20 万元的部分，可提成 5%;40 万到 60 万之间 时高于
40 万元的部分，可提成 3%;60 万到 100 万之间时，高于 60 万元的部分，可提成 1.5%，高于
100 万元时，超过 100 万元的部分按 1%提成，从键盘输入当月利润 I，求应发放奖 金总数?
'''
def fun2():
	b1 = 100000 * 0.1
	b2 = b1 + 100000 * 0.075
	b3 = b2 + 200000 * 0.05
	b4 = b3 + 200000 * 0.03
	b5 = b4 + 400000 * 0.015

	i = int(raw_input('input gain:\n'))
	if i <= 100000:
		result = i * 0.1
	elif i <= 200000:
		result = b1 + (i - 100000) * 0.075
	elif i <= 400000:
		reuslt = b2 + (i - 200000) * 0.05
	elif i <= 600000:
		result = b3 + (i - 400000) * 0.03
	elif i <= 100000:
		result = b4 + (i - 600000) * 0.015
	else:
		result = b5 + (i - 1000000) * 0.001
	print result


# 3 一个整数，它加上 100 后是一个完全平方数，再加上 168 又是一个完全平方数，请问该数是多少?
def fun3():
	import math
	for i in range(10000):
		if (int(math.sqrt(i + 100)) * int(math.sqrt(i + 100)) == i + 100) \
		and (int(math.sqrt(i + 168)) * int(math.sqrt(i + 168)) == i + 168):
				print i
				break


if __name__ == '__main__':
	fun3()
	