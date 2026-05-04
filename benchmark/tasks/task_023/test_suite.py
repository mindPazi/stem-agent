from solution import transpose

def test_2x2():
    assert transpose([[1,2],[3,4]]) == [[1,3],[2,4]]

def test_3x3():
    m = [[1,2,3],[4,5,6],[7,8,9]]
    assert transpose(m) == [[1,4,7],[2,5,8],[3,6,9]]

def test_identity():
    assert transpose([[1,0],[0,1]]) == [[1,0],[0,1]]
