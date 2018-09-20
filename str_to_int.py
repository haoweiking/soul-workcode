

def is_number(char):
    try:
        int(char)
        return True
    except ValueError as ve:
        print(ve)
        return False


def str_to_int(str_arr):
    if not str_arr:
        return None
    number = 0
    negative = False
    first = True
    for i in str_arr:
        if i == '-' and first:
            negative = True
            first = False
            continue
        if not is_number(i):
            return None
        print(i)
        number = number * 10 + int(i)
        first = False
    if negative:
        number = 0 - number
    return number


if __name__ == '__main__':
    a = '-100000000000000000000000000000000000000000000000000'
    print(str_to_int(a))
    b = '…………'
    print(str_to_int(b))

    # print(2**1000000000)
