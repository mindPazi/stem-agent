from solution import double_all

def test_basic():
    result = double_all([1, 2, 3])
    assert result == [2, 4, 6]

def test_empty():
    assert double_all([]) == []

def test_type():
    assert isinstance(double_all([1]), list)
