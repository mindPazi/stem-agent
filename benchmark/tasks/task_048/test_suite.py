from solution import is_palindrome

def test_lower():
    assert is_palindrome("racecar") is True

def test_mixed_case():
    assert is_palindrome("Racecar") is True

def test_phrase():
    assert is_palindrome("A man a plan a canal Panama") is True

def test_not():
    assert is_palindrome("hello") is False
