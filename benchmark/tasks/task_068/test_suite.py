from solution import set_difference

def test_basic():
    assert set_difference([1, 2, 3, 4], [3, 4, 5]) == [1, 2]

def test_empty_result():
    assert set_difference([1, 2], [1, 2, 3]) == []

def test_no_overlap():
    assert set_difference([1, 2], [3, 4]) == [1, 2]
