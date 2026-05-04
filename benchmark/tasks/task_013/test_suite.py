from solution import reverse_string

def test_even():
    assert reverse_string("abcd") == "dcba"

def test_odd():
    assert reverse_string("abcde") == "edcba"

def test_single():
    assert reverse_string("a") == "a"

def test_two():
    assert reverse_string("ab") == "ba"

def test_palindrome():
    assert reverse_string("racecar") == "racecar"
