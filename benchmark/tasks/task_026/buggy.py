def count_vowels(s):
    consonants = set('bcdfghjklmnpqrstvwxyz')
    return sum(1 for ch in s.lower() if ch in consonants)
