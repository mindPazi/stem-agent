from solution import list_average

def test_basic():
    assert list_average([1, 2, 3, 4]) == 2.5

def test_empty():
    assert list_average([]) is None

def test_single():
    assert list_average([5]) == 5.0

def test_negative():
    assert list_average([-1, 1]) == 0.0
