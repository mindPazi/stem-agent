from solution import sum_with_initial

def test_zero():
    assert sum_with_initial([1, 2, 3], 0) == 6

def test_initial():
    assert sum_with_initial([1, 2, 3], 10) == 16

def test_empty():
    assert sum_with_initial([], 5) == 5
