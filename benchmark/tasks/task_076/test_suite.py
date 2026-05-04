from solution import add_elements_to_set

def test_basic():
    result = add_elements_to_set({1, 2}, [3, 4])
    assert result == {1, 2, 3, 4}

def test_duplicates():
    result = add_elements_to_set({1, 2}, [2, 3])
    assert result == {1, 2, 3}

def test_empty():
    result = add_elements_to_set(set(), [1, 2])
    assert result == {1, 2}
