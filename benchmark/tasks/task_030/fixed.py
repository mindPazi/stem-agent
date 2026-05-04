import math

def safe_sqrt(n):
    if n < 0:
        return None
    return math.sqrt(n)
