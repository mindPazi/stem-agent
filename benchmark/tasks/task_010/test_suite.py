from solution import caesar_cipher

def test_shift3():
    assert caesar_cipher("abc", 3) == "def"

def test_shift1():
    assert caesar_cipher("z", 1) == "a"

def test_uppercase():
    assert caesar_cipher("ABC", 3) == "DEF"

def test_non_alpha():
    assert caesar_cipher("a b", 1) == "b c"

def test_shift26():
    assert caesar_cipher("abc", 26) == "abc"
