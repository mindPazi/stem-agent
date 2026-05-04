from solution import rotate_list

def test_rotate_basic():
    assert rotate_list([1, 2, 3, 4, 5], 2) == [3, 4, 5, 1, 2]

def test_rotate_one():
    assert rotate_list([1, 2, 3], 1) == [2, 3, 1]

def test_rotate_full():
    assert rotate_list([1, 2, 3], 3) == [1, 2, 3]

def test_rotate_zero():
    assert rotate_list([1, 2, 3], 0) == [1, 2, 3]

def test_rotate_empty():
    assert rotate_list([], 2) == []
