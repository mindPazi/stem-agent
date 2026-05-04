from solution import compress_string

def test_basic():
    assert compress_string("aabbbcc") == "a2b3c2"

def test_no_compress():
    assert compress_string("abc") == "a1b1c1"

def test_all_same():
    assert compress_string("aaaa") == "a4"

def test_single():
    assert compress_string("x") == "x1"
