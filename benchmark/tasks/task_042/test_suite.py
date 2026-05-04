from solution import parse_int

def test_positive():
    assert parse_int("42") == 42

def test_negative():
    assert parse_int("-5") == -5

def test_spaces():
    assert parse_int("  10  ") == 10

def test_zero():
    assert parse_int("0") == 0
