from solution import longest_common_prefix

def test_shorter_string():
    assert longest_common_prefix(["ba", "b"]) == "b"

def test_basic():
    assert longest_common_prefix(["flower", "flow", "flight"]) == "fl"

def test_none():
    assert longest_common_prefix(["dog", "racecar", "car"]) == ""

def test_one():
    assert longest_common_prefix(["alone"]) == "alone"
