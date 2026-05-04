from solution import rank_items

def test_basic():
    assert rank_items(['a', 'b', 'c']) == [(1, 'a'), (2, 'b'), (3, 'c')]

def test_single():
    assert rank_items(['x']) == [(1, 'x')]

def test_empty():
    assert rank_items([]) == []
