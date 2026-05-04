def list_depth(lst):
    if not isinstance(lst, list):
        return 0
    return 1 + max(list_depth(item) for item in lst)
