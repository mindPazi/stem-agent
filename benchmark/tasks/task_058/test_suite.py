from solution import flatten

def test_basic():
    assert flatten([1, [2, 3], [4, [5]]]) == [1, 2, 3, 4, 5]

def test_flat():
    assert flatten([1, 2, 3]) == [1, 2, 3]

def test_empty():
    assert flatten([]) == []

def test_deep():
    assert flatten([[[1]], [2]]) == [1, 2]
