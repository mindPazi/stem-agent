from solution import find_max

def test_basic():
    assert find_max([3, 1, 4, 1, 5, 9, 2, 6]) == 9

def test_all_negative():
    assert find_max([-5, -1, -3]) == -1

def test_single():
    assert find_max([7]) == 7

def test_negatives_and_positives():
    assert find_max([-10, 5, 3]) == 5
