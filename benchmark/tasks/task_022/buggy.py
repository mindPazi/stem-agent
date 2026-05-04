def word_count(sentence):
    counts = {}
    for word in sentence.split():
        counts[sentence] = counts.get(sentence, 0) + 1
    return counts
