from solution import remove_item

def test_found():
    assert remove_item([1, 2, 3], 2) == [1, 3]

def test_not_found():
    assert remove_item([1, 2, 3], 5) == [1, 2, 3]

def test_empty():
    assert remove_item([], 1) == []
