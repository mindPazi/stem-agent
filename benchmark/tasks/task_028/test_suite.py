from solution import safe_divide

def test_normal():
    assert safe_divide(10, 2) == 5.0

def test_zero_denominator():
    assert safe_divide(5, 0) is None

def test_negative():
    assert safe_divide(-6, 3) == -2.0

def test_float():
    assert safe_divide(1, 4) == 0.25
