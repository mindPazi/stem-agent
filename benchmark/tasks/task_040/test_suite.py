from solution import safe_pop

def test_normal():
    lst = [1, 2, 3]
    assert safe_pop(lst) == 3

def test_empty():
    assert safe_pop([]) is None

def test_single():
    lst = [42]
    assert safe_pop(lst) == 42
    assert lst == []
