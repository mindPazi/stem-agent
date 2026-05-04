from solution import list_to_string

def test_basic():
    assert list_to_string(['a', 'b', 'c']) == "abc"

def test_numbers():
    assert list_to_string([1, 2, 3]) == "123"

def test_empty():
    assert list_to_string([]) == ""
