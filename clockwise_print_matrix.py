# coding:utf-8


# 顺时针打印
mat = [[1,2,3,4],
       [5,6,7,8],
       [9,10,11,12],
       [13,14,15,16]]

i = 0
j = 0
result = []
z = len(mat)
h = len(mat[0])

d = 0

control = 0

while (len(result) < z * h):
    if mat[i][j] not in result:
        result.append(mat[i][j])

    if d % 4 == 0:
        j += 1
        if j == h - control - 1:
            d += 1
    elif d % 4 == 1:
        i += 1
        if i == z - control - 1:
            d += 1
    elif d % 4 == 2:
        j -= 1
        if j == control:
            d += 1
    else:
        i -= 1
        if i == control + 1:
            d += 1
            control += 1

    print(i, j, result)
print(result)

