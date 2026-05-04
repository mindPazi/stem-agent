from solution import stack_peek

def test_normal():
    assert stack_peek([1, 2, 3]) == 3

def test_empty():
    assert stack_peek([]) is None

def test_single():
    assert stack_peek([42]) == 42
