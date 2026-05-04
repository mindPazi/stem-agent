from solution import find_min

def test_basic():
    assert find_min([3, 1, 4, 1, 5]) == 1

def test_all_positive():
    assert find_min([5, 3, 7]) == 3

def test_all_negative():
    assert find_min([-1, -5, -2]) == -5

def test_single():
    assert find_min([42]) == 42
