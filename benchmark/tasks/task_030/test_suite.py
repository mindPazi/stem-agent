from solution import safe_sqrt

def test_positive():
    assert safe_sqrt(4) == 2.0

def test_zero():
    assert safe_sqrt(0) == 0.0

def test_negative():
    assert safe_sqrt(-1) is None

def test_float():
    import math
    assert math.isclose(safe_sqrt(2), math.sqrt(2))
