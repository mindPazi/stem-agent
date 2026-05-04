from solution import max_in_matrix

def test_basic():
    assert max_in_matrix([[1,2],[3,4]]) == 4

def test_empty():
    assert max_in_matrix([]) is None

def test_single():
    assert max_in_matrix([[7]]) == 7

def test_negatives():
    assert max_in_matrix([[-5, -3], [-10, -1]]) == -1
