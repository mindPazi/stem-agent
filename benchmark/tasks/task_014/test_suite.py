from solution import majority_element

def test_clear_majority():
    assert majority_element([3, 2, 3]) == 3

def test_even_no_majority():
    # [1,1,2,2] -> no majority (each appears exactly n//2 times)
    assert majority_element([1, 1, 2, 2]) == -1

def test_all_same():
    assert majority_element([5, 5, 5]) == 5

def test_two_elements():
    assert majority_element([1, 1]) == 1
