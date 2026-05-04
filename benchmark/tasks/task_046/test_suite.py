from solution import factorial

def test_zero():
    assert factorial(0) == 1

def test_one():
    assert factorial(1) == 1

def test_five():
    assert factorial(5) == 120

def test_six():
    assert factorial(6) == 720
