from solution import remove_vowels

def test_basic():
    assert remove_vowels("hello") == "hll"

def test_all_vowels():
    assert remove_vowels("aeiou") == ""

def test_no_vowels():
    assert remove_vowels("rhythm") == "rhythm"

def test_mixed():
    assert remove_vowels("Python") == "Pythn"
