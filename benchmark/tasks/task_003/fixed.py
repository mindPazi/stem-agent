def rotate_list(lst, k):
    if not lst:
        return lst
    k = k % len(lst)
    return lst[k:] + lst[:k]
