from solution import sort_by_length

def test_basic():
    assert sort_by_length(["banana", "apple", "fig", "cherry"]) == ["fig", "apple", "banana", "cherry"]

def test_equal():
    result = sort_by_length(["ab", "cd"])
    assert len(result[0]) <= len(result[1])

def test_single():
    assert sort_by_length(["hello"]) == ["hello"]
