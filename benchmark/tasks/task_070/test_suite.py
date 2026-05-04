from solution import is_integer

def test_int():
    assert is_integer(5) is True

def test_float():
    assert is_integer(5.0) is False

def test_bool():
    # bool is a subclass of int; isinstance catches this
    assert is_integer(True) is True

def test_string():
    assert is_integer("5") is False
