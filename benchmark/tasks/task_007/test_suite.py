from solution import max_sliding_window

def test_k2():
    assert max_sliding_window([1, 3, -1, -3, 5, 3, 6, 7], 2) == [3, 3, -1, 5, 5, 6, 7]

def test_k3():
    assert max_sliding_window([1, 3, -1, -3, 5, 3, 6, 7], 3) == [3, 3, 5, 5, 6, 7]

def test_k1():
    assert max_sliding_window([4, 2, 1], 1) == [4, 2, 1]

def test_full_window():
    assert max_sliding_window([1, 2, 3], 3) == [3]
