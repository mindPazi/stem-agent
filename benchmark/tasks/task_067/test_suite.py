from solution import is_close_to_zero

def test_zero():
    assert is_close_to_zero(0.0) is True

def test_near_zero():
    assert is_close_to_zero(1e-10) is True

def test_not_zero():
    assert is_close_to_zero(0.1) is False

def test_neg_near_zero():
    assert is_close_to_zero(-1e-10) is True
