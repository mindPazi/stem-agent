from solution import word_count

def test_basic():
    assert word_count("hello world hello") == {"hello": 2, "world": 1}

def test_single():
    assert word_count("one") == {"one": 1}

def test_multiple():
    result = word_count("a b a c a")
    assert result == {"a": 3, "b": 1, "c": 1}
