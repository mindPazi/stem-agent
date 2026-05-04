from solution import is_anagram

def test_different_lengths():
    assert is_anagram("a", "ab") is False

def test_anagram():
    assert is_anagram("anagram", "nagaram") is True

def test_not_anagram():
    assert is_anagram("rat", "car") is False

def test_same():
    assert is_anagram("a", "a") is True
