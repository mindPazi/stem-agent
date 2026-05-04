def is_palindrome(s):
    cleaned = ''.join(ch for ch in s if ch.isalnum())
    return cleaned == cleaned[::-1]
