from solution import count_substrings

def test_full_match():
    assert count_substrings("abc", "abc") == 1

def test_basic():
    assert count_substrings("hello", "l") == 2

def test_none():
    assert count_substrings("hello", "z") == 0

def test_last_position():
    assert count_substrings("abab", "ab") == 2
