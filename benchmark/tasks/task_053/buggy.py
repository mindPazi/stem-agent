def count_occurrences(lst, target):
    return sum(1 for item in lst if item != target)
