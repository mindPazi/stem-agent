from solution import max_subarray

def test_basic():
    assert max_subarray([-2, 1, -3, 4, -1, 2, 1, -5, 4]) == 6

def test_all_negative():
    assert max_subarray([-1, -2, -3]) == -1

def test_all_positive():
    assert max_subarray([1, 2, 3]) == 6

def test_single():
    assert max_subarray([5]) == 5
