from solution import title_case

def test_basic():
    assert title_case("hello world") == "Hello World"

def test_already():
    assert title_case("Python Is Fun") == "Python Is Fun"

def test_all_lower():
    assert title_case("foo bar") == "Foo Bar"

def test_empty():
    assert title_case("") == ""
