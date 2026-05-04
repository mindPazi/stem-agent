def count_substrings(s, sub):
    count = 0
    for i in range(len(s) - len(sub) + 1):
        if s[i:i + len(sub)] == sub:
            count += 1
    return count
