def remove_vowels(s):
    vowels = set('aeiouAEIOU')
    return ''.join(ch for ch in s if ch not in vowels)
