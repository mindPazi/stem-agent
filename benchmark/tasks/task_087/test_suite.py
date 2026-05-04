from solution import quicksort

def test_basic():
    assert quicksort([3, 6, 8, 10, 1, 2, 1]) == [1, 1, 2, 3, 6, 8, 10]

def test_duplicates():
    assert quicksort([3, 3, 3]) == [3, 3, 3]

def test_empty():
    assert quicksort([]) == []

def test_single():
    assert quicksort([1]) == [1]

def test_sorted():
    assert quicksort([1, 2, 3, 4, 5]) == [1, 2, 3, 4, 5]
