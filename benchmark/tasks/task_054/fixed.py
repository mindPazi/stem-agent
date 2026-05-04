def is_balanced(s):
    count = 0
    for ch in s:
        if ch == '(':
            count += 1
        elif ch == ')':
            count -= 1
        if count < 0:
            return False
    return count == 0
