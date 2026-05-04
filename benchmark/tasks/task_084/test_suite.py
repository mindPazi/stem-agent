from solution import is_palindrome

def test_single_char():
    assert is_palindrome("a") is True

def test_palindrome():
    assert is_palindrome("racecar") is True

def test_not_palindrome():
    assert is_palindrome("hello") is False

def test_empty():
    assert is_palindrome("") is True
