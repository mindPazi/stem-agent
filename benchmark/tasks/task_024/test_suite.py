from solution import capitalize_words

def test_basic():
    assert capitalize_words("hello world") == "Hello World"

def test_already():
    assert capitalize_words("Python Is Great") == "Python Is Great"

def test_lower():
    assert capitalize_words("foo bar baz") == "Foo Bar Baz"
