def sort_by_length(words):
    return sorted(words, key=lambda w: -len(w))
