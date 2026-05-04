from solution import count_digits

def test_zero():
    assert count_digits(0) == 1

def test_single():
    assert count_digits(5) == 1

def test_two():
    assert count_digits(42) == 2

def test_negative():
    assert count_digits(-123) == 3
