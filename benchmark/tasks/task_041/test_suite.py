from solution import safe_dict_get

def test_found():
    assert safe_dict_get({"a": 1}, "a") == 1

def test_missing():
    assert safe_dict_get({"a": 1}, "b") is None

def test_default():
    assert safe_dict_get({"a": 1}, "b", 42) == 42
