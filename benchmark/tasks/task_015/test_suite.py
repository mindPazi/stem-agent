from solution import trap_rain_water

def test_basic():
    assert trap_rain_water([0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1]) == 6

def test_two_walls():
    assert trap_rain_water([3, 0, 3]) == 3

def test_no_water():
    assert trap_rain_water([3, 2, 1]) == 0

def test_short():
    assert trap_rain_water([1, 2]) == 0
