def power(base, exponent):
    result = 1
    for _ in range(base):
        result *= exponent
    return result
