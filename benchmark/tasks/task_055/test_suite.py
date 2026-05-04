from solution import gcd_recursive

def test_basic():
    assert gcd_recursive(48, 18) == 6

def test_coprime():
    assert gcd_recursive(7, 13) == 1

def test_same():
    assert gcd_recursive(5, 5) == 5

def test_multiples():
    assert gcd_recursive(100, 25) == 25
