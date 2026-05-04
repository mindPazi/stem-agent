def reverse_string(s):
    lst = list(s)
    n = len(lst)
    for i in range(n // 2):
        lst[i], lst[n - 1 - i] = lst[n - 1 - i], lst[i]
    return ''.join(lst)
