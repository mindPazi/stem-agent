from solution import sorted_copy

def test_basic():
    result = sorted_copy([3, 1, 2])
    assert result == [1, 2, 3]

def test_unchanged_original():
    original = [3, 1, 2]
    result = sorted_copy(original)
    assert result is not None
    assert original == [3, 1, 2]

def test_empty():
    assert sorted_copy([]) == []
