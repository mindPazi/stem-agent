def count_vowels(s):
    vowels = set('aeiou')
    return sum(1 for ch in s.lower() if ch in vowels)
