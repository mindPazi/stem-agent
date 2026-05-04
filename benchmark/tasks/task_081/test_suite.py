from solution import find_max_loop

def test_single():
    assert find_max_loop([42]) == 42

def test_multiple():
    assert find_max_loop([3, 1, 4, 1, 5]) == 5

def test_negatives():
    assert find_max_loop([-5, -1, -3]) == -1
