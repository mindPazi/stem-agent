from solution import run_length_encode

def test_single():
    assert run_length_encode("a") == "1a"

def test_no_repeat():
    assert run_length_encode("abc") == "1a1b1c"

def test_basic():
    assert run_length_encode("aabbbcc") == "2a3b2c"

def test_all_same():
    assert run_length_encode("aaaa") == "4a"

def test_empty():
    assert run_length_encode("") == ""
