from solution import two_sum_exists

def test_found():
    assert two_sum_exists([2, 7, 11, 15], 9) is True

def test_not_found():
    assert two_sum_exists([1, 2, 3], 10) is False

def test_two_elements():
    assert two_sum_exists([3, 7], 10) is True

def test_negative():
    assert two_sum_exists([-1, 4, 5], 3) is True
