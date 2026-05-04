from solution import is_prime

def test_prime():
    assert is_prime(7) is True

def test_not_prime():
    assert is_prime(9) is False

def test_one():
    assert is_prime(1) is False

def test_zero():
    assert is_prime(0) is False

def test_two():
    assert is_prime(2) is True

def test_large():
    assert is_prime(97) is True
