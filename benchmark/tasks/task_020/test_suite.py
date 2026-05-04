from solution import find_second_largest

def test_basic():
    assert find_second_largest([3, 1, 4, 1, 5, 9, 2, 6]) == 6

def test_two_elements():
    assert find_second_largest([10, 5]) == 5

def test_negatives():
    assert find_second_largest([-1, -2, -3]) == -2

def test_three():
    assert find_second_largest([1, 2, 3]) == 2
