from solution import get_diagonal

def test_3x3():
    assert get_diagonal([[1,2,3],[4,5,6],[7,8,9]]) == [1, 5, 9]

def test_2x2():
    assert get_diagonal([[1,2],[3,4]]) == [1, 4]

def test_1x1():
    assert get_diagonal([[7]]) == [7]
