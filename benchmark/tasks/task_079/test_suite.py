from solution import find_longest

def test_basic():
    assert find_longest(["hi", "hello", "hey"]) == "hello"

def test_single():
    assert find_longest(["word"]) == "word"

def test_tie():
    result = find_longest(["ab", "cd"])
    assert len(result) == 2
