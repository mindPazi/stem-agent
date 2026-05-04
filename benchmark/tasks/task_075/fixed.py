def remove_suffix_ing(word):
    if word.endswith('ing'):
        return word[:-3]
    return word
