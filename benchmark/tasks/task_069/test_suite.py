from solution import sum_values

def test_basic():
    assert sum_values({"a": 1, "b": 2, "c": 3}) == 6

def test_single():
    assert sum_values({"x": 10}) == 10

def test_zero():
    assert sum_values({"a": 0, "b": 0}) == 0
