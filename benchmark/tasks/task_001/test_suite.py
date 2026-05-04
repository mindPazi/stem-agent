import pytest
from solution import binary_search

def test_found_middle():
    assert binary_search([1, 3, 5, 7, 9], 5) == 2

def test_found_first():
    assert binary_search([1, 3, 5, 7, 9], 1) == 0

def test_found_last():
    assert binary_search([1, 3, 5, 7, 9], 9) == 4

def test_not_found_larger():
    # triggers IndexError on buggy version when mid reaches len(arr)
    assert binary_search([1, 3, 5, 7, 9], 10) == -1

def test_not_found_smaller():
    assert binary_search([1, 3, 5, 7, 9], 0) == -1

def test_single_element_found():
    assert binary_search([42], 42) == 0
