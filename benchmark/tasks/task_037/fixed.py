def remove_item(lst, item):
    lst = list(lst)
    if item in lst:
        lst.remove(item)
    return lst
