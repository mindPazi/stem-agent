from solution import combine_lists

def test_basic():
    assert combine_lists([1, 2], [3, 4]) == [1, 2, 3, 4]

def test_empty_b():
    assert combine_lists([1, 2], []) == [1, 2]

def test_empty_a():
    assert combine_lists([], [1, 2]) == [1, 2]
