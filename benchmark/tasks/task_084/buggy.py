def is_palindrome(s):
    if len(s) < 2:
        return False
    return s == s[::-1]
