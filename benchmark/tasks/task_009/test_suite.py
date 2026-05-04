import pytest
from solution import diagonal_sum

def test_3x3():
    assert diagonal_sum([[1,2,3],[4,5,6],[7,8,9]]) == 15

def test_2x2():
    assert diagonal_sum([[1,2],[3,4]]) == 5

def test_1x1():
    assert diagonal_sum([[7]]) == 7
