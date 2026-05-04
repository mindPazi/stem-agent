from solution import safe_log

def test_positive():
    import math
    assert math.isclose(safe_log(math.e), 1.0)

def test_zero():
    assert safe_log(0) is None

def test_negative():
    assert safe_log(-5) is None

def test_one():
    assert safe_log(1) == 0.0
