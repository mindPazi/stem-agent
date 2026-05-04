from solution import remove_duplicates

def test_no_dups():
    assert remove_duplicates([1, 2, 3]) == [1, 2, 3]

def test_all_same():
    assert remove_duplicates([5, 5, 5]) == [5]

def test_empty():
    assert remove_duplicates([]) == []

def test_single():
    assert remove_duplicates([7]) == [7]

def test_trailing():
    assert remove_duplicates([1, 2, 2]) == [1, 2]
