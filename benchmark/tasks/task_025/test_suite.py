from solution import power

def test_basic():
    assert power(2, 3) == 8

def test_one():
    assert power(5, 1) == 5

def test_zero_exp():
    assert power(7, 0) == 1

def test_ten():
    assert power(10, 2) == 100
