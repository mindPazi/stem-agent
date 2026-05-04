from solution import is_sorted

def test_sorted():
    assert is_sorted([1, 2, 3]) is True

def test_equal_consecutive():
    assert is_sorted([1, 1, 2]) is True

def test_unsorted():
    assert is_sorted([2, 1]) is False

def test_empty():
    assert is_sorted([]) is True
