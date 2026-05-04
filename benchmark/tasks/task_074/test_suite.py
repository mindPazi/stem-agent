from solution import group_by_length

def test_basic():
    result = group_by_length(["hi", "bye", "go", "no"])
    assert sorted(result[2]) == ["go", "hi", "no"]
    assert result[3] == ["bye"]

def test_single():
    assert group_by_length(["hello"]) == {5: ["hello"]}

def test_empty():
    assert group_by_length([]) == {}
