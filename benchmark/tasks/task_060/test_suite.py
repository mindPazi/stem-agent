from solution import product_of_list

def test_basic():
    assert product_of_list([1, 2, 3, 4]) == 24

def test_single():
    assert product_of_list([5]) == 5

def test_with_zero():
    assert product_of_list([1, 2, 0, 4]) == 0

def test_negatives():
    assert product_of_list([-1, -2, 3]) == 6
