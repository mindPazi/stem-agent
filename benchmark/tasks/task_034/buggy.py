def count_digits(n):
    n = abs(n)
    count = 0
    while n > 0:
        n //= 10
        count += 1
    return count
