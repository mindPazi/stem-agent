from solution import max_number_string

def test_basic():
    assert max_number_string(["10", "9", "100"]) == "100"

def test_single():
    assert max_number_string(["5"]) == "5"

def test_same_digits():
    assert max_number_string(["21", "22", "20"]) == "22"
