from solution import bubble_sort

def test_basic():
    assert bubble_sort([64, 34, 25, 12, 22, 11, 90]) == [11, 12, 22, 25, 34, 64, 90]

def test_sorted():
    assert bubble_sort([1, 2, 3]) == [1, 2, 3]

def test_reverse():
    assert bubble_sort([3, 2, 1]) == [1, 2, 3]

def test_single():
    assert bubble_sort([1]) == [1]
