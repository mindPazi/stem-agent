from solution import get_words

def test_basic():
    assert get_words("hello world") == ["hello", "world"]

def test_empty():
    assert get_words("") == []

def test_extra_spaces():
    assert get_words("hello  world") == ["hello", "world"]
