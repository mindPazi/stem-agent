from solution import sum_of_squares

def test_basic():
    assert sum_of_squares([1, 2, 3]) == 14

def test_single():
    assert sum_of_squares([4]) == 16

def test_zeros():
    assert sum_of_squares([0, 0]) == 0
