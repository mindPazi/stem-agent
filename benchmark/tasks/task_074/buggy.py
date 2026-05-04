def group_by_length(words):
    groups = {}
    for word in words:
        key = len(word)
        groups[key] = [word]
    return groups
