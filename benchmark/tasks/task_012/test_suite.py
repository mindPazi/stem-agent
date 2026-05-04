from solution import next_greater_element

def test_equal_elements():
    assert next_greater_element([3, 3, 5]) == [5, 5, -1]

def test_basic():
    assert next_greater_element([4, 5, 2, 10]) == [5, 10, 10, -1]

def test_descending():
    assert next_greater_element([5, 4, 3]) == [-1, -1, -1]

def test_single():
    assert next_greater_element([1]) == [-1]
