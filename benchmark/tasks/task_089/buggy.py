def repeat_string(s, n):
    result = s
    for _ in range(n - 1):
        result += s
    return result
