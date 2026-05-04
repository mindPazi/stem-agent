from solution import zip_fill

def test_equal():
    assert zip_fill([1, 2], ['a', 'b']) == [(1, 'a'), (2, 'b')]

def test_longer_a():
    assert zip_fill([1, 2, 3], ['a', 'b']) == [(1, 'a'), (2, 'b'), (3, None)]

def test_longer_b():
    assert zip_fill([1], ['a', 'b', 'c']) == [(1, 'a'), (None, 'b'), (None, 'c')]
