from solution import repeat_string

def test_basic():
    assert repeat_string("ab", 3) == "ababab"

def test_once():
    assert repeat_string("hello", 1) == "hello"

def test_zero():
    assert repeat_string("hi", 0) == ""

def test_empty_string():
    assert repeat_string("", 5) == ""
