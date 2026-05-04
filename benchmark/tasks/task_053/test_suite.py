from solution import count_occurrences

def test_basic():
    assert count_occurrences([1, 2, 2, 3, 2], 2) == 3

def test_none():
    assert count_occurrences([1, 2, 3], 5) == 0

def test_all():
    assert count_occurrences([4, 4, 4], 4) == 3
