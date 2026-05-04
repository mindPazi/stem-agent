from solution import remove_suffix_ing

def test_basic():
    assert remove_suffix_ing("running") == "runn"

def test_no_suffix():
    assert remove_suffix_ing("hello") == "hello"

def test_just_ing():
    assert remove_suffix_ing("ing") == ""

def test_singing():
    assert remove_suffix_ing("singing") == "sing"
