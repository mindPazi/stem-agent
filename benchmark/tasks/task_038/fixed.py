import math

def safe_log(n):
    if n <= 0:
        return None
    return math.log(n)
