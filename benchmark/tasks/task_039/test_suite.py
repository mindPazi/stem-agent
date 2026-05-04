from solution import list_depth

def test_flat():
    assert list_depth([1, 2, 3]) == 1

def test_nested():
    assert list_depth([1, [2, [3]]]) == 3

def test_empty():
    assert list_depth([]) == 1

def test_scalar():
    assert list_depth(5) == 0
