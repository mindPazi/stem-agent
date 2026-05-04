from solution import count_evens

def test_basic():
    assert count_evens([1, 2, 3, 4, 5]) == 2

def test_all_even():
    assert count_evens([2, 4, 6]) == 3

def test_all_odd():
    assert count_evens([1, 3, 5]) == 0

def test_empty():
    assert count_evens([]) == 0
