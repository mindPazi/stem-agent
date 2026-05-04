from solution import average

def test_exact():
    assert average([1, 2, 3]) == 2.0

def test_fractional():
    assert average([1, 2]) == 1.5

def test_negatives():
    assert average([-1, 1]) == 0.0
