from solution import fizzbuzz

def test_15():
    result = fizzbuzz(15)
    assert result[14] == 'FizzBuzz'

def test_3():
    result = fizzbuzz(5)
    assert result[2] == 'Fizz'

def test_5():
    result = fizzbuzz(5)
    assert result[4] == 'Buzz'

def test_1():
    result = fizzbuzz(1)
    assert result[0] == '1'
