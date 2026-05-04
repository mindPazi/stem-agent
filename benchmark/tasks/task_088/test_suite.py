from solution import safe_mod

def test_normal():
    assert safe_mod(10, 3) == 1

def test_zero_divisor():
    assert safe_mod(5, 0) is None

def test_exact():
    assert safe_mod(6, 3) == 0
