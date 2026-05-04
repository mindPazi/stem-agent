from itertools import zip_longest

def zip_fill(a, b, fill=None):
    return list(zip_longest(a, b, fillvalue=fill))
