from solution import count_vowels

def test_basic():
    assert count_vowels("hello") == 2

def test_none():
    assert count_vowels("sky") == 0

def test_all_vowels():
    assert count_vowels("aeiou") == 5

def test_mixed():
    assert count_vowels("Python") == 1
