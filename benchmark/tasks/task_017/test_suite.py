from solution import gcd

def test_basic():
    assert gcd(48, 18) == 6

def test_coprime():
    assert gcd(7, 13) == 1

def test_same():
    assert gcd(5, 5) == 5

def test_one():
    assert gcd(1, 100) == 1

def test_multiples():
    assert gcd(100, 25) == 25
