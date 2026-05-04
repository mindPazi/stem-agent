from solution import join_numbers

def test_basic():
    assert join_numbers([1, 2, 3]) == "1, 2, 3"

def test_empty():
    assert join_numbers([]) == ""

def test_single():
    assert join_numbers([42]) == "42"

def test_custom_sep():
    assert join_numbers([1, 2, 3], "-") == "1-2-3"
