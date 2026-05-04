from solution import is_balanced

def test_balanced():
    assert is_balanced("(())") is True

def test_unbalanced():
    assert is_balanced("(()") is False

def test_empty():
    assert is_balanced("") is True

def test_simple():
    assert is_balanced("()") is True

def test_wrong_order():
    assert is_balanced(")(") is False
