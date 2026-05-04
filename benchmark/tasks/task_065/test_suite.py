from solution import number_to_string

def test_int():
    assert number_to_string(42) == "42"

def test_zero():
    assert number_to_string(0) == "0"

def test_negative():
    assert number_to_string(-5) == "-5"

def test_type():
    assert isinstance(number_to_string(1), str)
