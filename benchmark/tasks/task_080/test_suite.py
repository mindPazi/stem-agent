from solution import filter_positive

def test_basic():
    assert filter_positive([1, -2, 3, -4]) == [1, 3]

def test_all_negative():
    assert filter_positive([-1, -2]) == []

def test_type():
    assert isinstance(filter_positive([1, 2]), list)
