from solution import count_pairs_with_sum

def test_basic():
    assert count_pairs_with_sum([1, 5, 7, -1, 5], 6) == 3

def test_none():
    assert count_pairs_with_sum([1, 2, 3], 10) == 0

def test_one():
    assert count_pairs_with_sum([1, 9], 10) == 1
