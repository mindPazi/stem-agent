from solution import first_element

def test_normal():
    assert first_element([1, 2, 3]) == 1

def test_empty():
    assert first_element([]) is None

def test_single():
    assert first_element([99]) == 99
