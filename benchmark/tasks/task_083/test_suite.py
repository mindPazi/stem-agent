from solution import fib

def test_zero():
    assert fib(0) == 0

def test_one():
    assert fib(1) == 1

def test_two():
    assert fib(2) == 1

def test_five():
    assert fib(5) == 5
