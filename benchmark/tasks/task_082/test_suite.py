from solution import power

def test_zero_exp():
    assert power(5, 0) == 1

def test_one_exp():
    assert power(5, 1) == 5

def test_two_exp():
    assert power(3, 2) == 9

def test_zero_base():
    assert power(0, 3) == 0
