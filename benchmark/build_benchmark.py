"""
Build the benchmark: generates 90 self-contained Python bug repair tasks.
Each task: buggy.py (fails tests), fixed.py (passes tests), test_suite.py, metadata.json.
Source: hand-crafted mutation-based bugs (source="mutation_exercism").

Usage:
    python benchmark/build_benchmark.py [--validate]
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Task definitions
# Format: (task_id, category, difficulty, lines_changed, description, buggy, fixed, test)
# All test files import from `solution` (the file agent writes to).
# ---------------------------------------------------------------------------

TASKS: list[dict] = []


def T(
    task_id: str,
    category: str,
    difficulty: str,
    lines_changed: int,
    description: str,
    buggy: str,
    fixed: str,
    test: str,
) -> None:
    TASKS.append(
        {
            "task_id": task_id,
            "category": category,
            "difficulty": difficulty,
            "lines_changed": lines_changed,
            "description": description,
            "source": "mutation_exercism",
            "buggy": buggy,
            "fixed": fixed,
            "test": test,
        }
    )


# ===========================================================================
# OFF-BY-ONE (15 tasks)
# ===========================================================================

T(
    "task_001", "off_by_one", "easy", 1,
    "binary_search uses high=len(arr) causing IndexError when target exceeds all elements",
    buggy="""
def binary_search(arr, target):
    low, high = 0, len(arr)
    while low <= high:
        mid = (low + high) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1
""".strip(),
    fixed="""
def binary_search(arr, target):
    low, high = 0, len(arr) - 1
    while low <= high:
        mid = (low + high) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1
""".strip(),
    test="""
import pytest
from solution import binary_search

def test_found_middle():
    assert binary_search([1, 3, 5, 7, 9], 5) == 2

def test_found_first():
    assert binary_search([1, 3, 5, 7, 9], 1) == 0

def test_found_last():
    assert binary_search([1, 3, 5, 7, 9], 9) == 4

def test_not_found_larger():
    # triggers IndexError on buggy version when mid reaches len(arr)
    assert binary_search([1, 3, 5, 7, 9], 10) == -1

def test_not_found_smaller():
    assert binary_search([1, 3, 5, 7, 9], 0) == -1

def test_single_element_found():
    assert binary_search([42], 42) == 0
""".strip(),
)

T(
    "task_002", "off_by_one", "easy", 1,
    "Fibonacci returns fib(n-1) instead of fib(n) due to off-by-one in loop range",
    buggy="""
def fibonacci(n):
    if n <= 0:
        return 0
    a, b = 0, 1
    for _ in range(n - 1):
        a, b = b, a + b
    return a
""".strip(),
    fixed="""
def fibonacci(n):
    if n <= 0:
        return 0
    a, b = 0, 1
    for _ in range(n - 1):
        a, b = b, a + b
    return b
""".strip(),
    test="""
from solution import fibonacci

def test_fib_1():
    assert fibonacci(1) == 1

def test_fib_2():
    assert fibonacci(2) == 1

def test_fib_5():
    assert fibonacci(5) == 5

def test_fib_10():
    assert fibonacci(10) == 55

def test_fib_0():
    assert fibonacci(0) == 0
""".strip(),
)

T(
    "task_003", "off_by_one", "easy", 1,
    "rotate_list slices at k+1 instead of k, shifting one extra element",
    buggy="""
def rotate_list(lst, k):
    if not lst:
        return lst
    k = k % len(lst)
    return lst[k + 1:] + lst[:k + 1]
""".strip(),
    fixed="""
def rotate_list(lst, k):
    if not lst:
        return lst
    k = k % len(lst)
    return lst[k:] + lst[:k]
""".strip(),
    test="""
from solution import rotate_list

def test_rotate_basic():
    assert rotate_list([1, 2, 3, 4, 5], 2) == [3, 4, 5, 1, 2]

def test_rotate_one():
    assert rotate_list([1, 2, 3], 1) == [2, 3, 1]

def test_rotate_full():
    assert rotate_list([1, 2, 3], 3) == [1, 2, 3]

def test_rotate_zero():
    assert rotate_list([1, 2, 3], 0) == [1, 2, 3]

def test_rotate_empty():
    assert rotate_list([], 2) == []
""".strip(),
)

T(
    "task_004", "off_by_one", "medium", 1,
    "count_substrings counts range(n+1) including invalid start index",
    buggy="""
def count_substrings(s, sub):
    count = 0
    n = len(s)
    for i in range(n + 1):
        if s[i:i + len(sub)] == sub:
            count += 1
    return count
""".strip(),
    fixed="""
def count_substrings(s, sub):
    count = 0
    n = len(s)
    for i in range(n):
        if s[i:i + len(sub)] == sub:
            count += 1
    return count
""".strip(),
    test="""
from solution import count_substrings

def test_basic():
    assert count_substrings("hello", "l") == 2

def test_overlap():
    assert count_substrings("aaa", "aa") == 2

def test_none():
    assert count_substrings("hello", "z") == 0

def test_full_match():
    assert count_substrings("abc", "abc") == 1
""".strip(),
)

T(
    "task_005", "off_by_one", "medium", 1,
    "insertion_sort inner loop range goes to n instead of i, comparing out of bounds",
    buggy="""
def insertion_sort(arr):
    n = len(arr)
    for i in range(1, n):
        key = arr[i]
        j = i - 1
        while j >= 0 and arr[j] > key:
            arr[j + 1] = arr[j]
            j -= 1
        arr[j + 1] = key
    return arr
""".strip(),
    fixed="""
def insertion_sort(arr):
    n = len(arr)
    for i in range(1, n):
        key = arr[i]
        j = i - 1
        while j >= 0 and arr[j] > key:
            arr[j + 1] = arr[j]
            j -= 1
        arr[j + 1] = key
    return arr
""".strip(),
    test="""
from solution import insertion_sort

def test_sorted():
    assert insertion_sort([3, 1, 2]) == [1, 2, 3]

def test_already_sorted():
    assert insertion_sort([1, 2, 3]) == [1, 2, 3]

def test_reverse():
    assert insertion_sort([5, 4, 3, 2, 1]) == [1, 2, 3, 4, 5]

def test_single():
    assert insertion_sort([1]) == [1]
""".strip(),
)

# task_005 is actually correct - let me use a real off-by-one for it
TASKS.pop()  # remove task_005 placeholder

T(
    "task_005", "off_by_one", "easy", 1,
    "remove_duplicates includes last element twice due to wrong range end",
    buggy="""
def remove_duplicates(arr):
    if not arr:
        return []
    result = [arr[0]]
    for i in range(1, len(arr) + 1):
        if i < len(arr) and arr[i] != arr[i - 1]:
            result.append(arr[i])
    return result
""".strip(),
    fixed="""
def remove_duplicates(arr):
    if not arr:
        return []
    result = [arr[0]]
    for i in range(1, len(arr)):
        if arr[i] != arr[i - 1]:
            result.append(arr[i])
    return result
""".strip(),
    test="""
from solution import remove_duplicates

def test_basic():
    assert remove_duplicates([1, 1, 2, 3, 3, 4]) == [1, 2, 3, 4]

def test_no_dups():
    assert remove_duplicates([1, 2, 3]) == [1, 2, 3]

def test_all_same():
    assert remove_duplicates([5, 5, 5]) == [5]

def test_empty():
    assert remove_duplicates([]) == []

def test_single():
    assert remove_duplicates([7]) == [7]
""".strip(),
)

T(
    "task_006", "off_by_one", "medium", 1,
    "find_peak_element checks arr[mid+1] without guarding against mid+1 == len(arr)",
    buggy="""
def find_peak(arr):
    low, high = 0, len(arr) - 1
    while low < high:
        mid = (low + high) // 2
        if arr[mid] < arr[mid + 1]:
            low = mid + 1
        else:
            high = mid
    return low
""".strip(),
    fixed="""
def find_peak(arr):
    low, high = 0, len(arr) - 1
    while low < high:
        mid = (low + high) // 2
        if arr[mid] < arr[mid + 1]:
            low = mid + 1
        else:
            high = mid
    return low
""".strip(),
    test="""
from solution import find_peak

def test_peak_middle():
    result = find_peak([1, 3, 2])
    assert result == 1

def test_peak_right():
    result = find_peak([1, 2, 3])
    assert result == 2

def test_peak_left():
    result = find_peak([3, 2, 1])
    assert result == 0

def test_single():
    assert find_peak([5]) == 0
""".strip(),
)

# task_006 is correct again. Let me replace with actual bugs.
TASKS.pop()

T(
    "task_006", "off_by_one", "easy", 1,
    "two_sum_indices returns 0-indexed but problem expects 1-indexed results",
    buggy="""
def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []
""".strip(),
    fixed="""
def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement] + 1, i + 1]
        seen[num] = i
    return []
""".strip(),
    test="""
from solution import two_sum

def test_basic():
    assert two_sum([2, 7, 11, 15], 9) == [1, 2]

def test_other_pair():
    assert two_sum([3, 2, 4], 6) == [2, 3]

def test_same_value():
    assert two_sum([3, 3], 6) == [1, 2]
""".strip(),
)

T(
    "task_007", "off_by_one", "medium", 1,
    "sliding_window_max uses window of size k+1 instead of k",
    buggy="""
def max_sliding_window(nums, k):
    result = []
    for i in range(len(nums) - k + 1):
        result.append(max(nums[i:i + k + 1]))
    return result
""".strip(),
    fixed="""
def max_sliding_window(nums, k):
    result = []
    for i in range(len(nums) - k + 1):
        result.append(max(nums[i:i + k]))
    return result
""".strip(),
    test="""
from solution import max_sliding_window

def test_k2():
    assert max_sliding_window([1, 3, -1, -3, 5, 3, 6, 7], 2) == [3, 3, -1, 5, 5, 6, 7]

def test_k3():
    assert max_sliding_window([1, 3, -1, -3, 5, 3, 6, 7], 3) == [3, 3, 5, 5, 6, 7]

def test_k1():
    assert max_sliding_window([4, 2, 1], 1) == [4, 2, 1]

def test_full_window():
    assert max_sliding_window([1, 2, 3], 3) == [3]
""".strip(),
)

T(
    "task_008", "off_by_one", "easy", 1,
    "count_pairs double-counts pairs by not starting inner loop at i+1",
    buggy="""
def count_pairs_with_sum(arr, target):
    count = 0
    n = len(arr)
    for i in range(n):
        for j in range(n):
            if i != j and arr[i] + arr[j] == target:
                count += 1
    return count // 2
""".strip(),
    fixed="""
def count_pairs_with_sum(arr, target):
    count = 0
    n = len(arr)
    for i in range(n):
        for j in range(i + 1, n):
            if arr[i] + arr[j] == target:
                count += 1
    return count
""".strip(),
    test="""
from solution import count_pairs_with_sum

def test_basic():
    assert count_pairs_with_sum([1, 5, 7, -1, 5], 6) == 3

def test_none():
    assert count_pairs_with_sum([1, 2, 3], 10) == 0

def test_one():
    assert count_pairs_with_sum([1, 9], 10) == 1
""".strip(),
)

T(
    "task_009", "off_by_one", "medium", 1,
    "matrix_diagonal_sum iterates range(n+1) causing IndexError on last iteration",
    buggy="""
def diagonal_sum(matrix):
    n = len(matrix)
    total = 0
    for i in range(n + 1):
        total += matrix[i][i]
    return total
""".strip(),
    fixed="""
def diagonal_sum(matrix):
    n = len(matrix)
    total = 0
    for i in range(n):
        total += matrix[i][i]
    return total
""".strip(),
    test="""
import pytest
from solution import diagonal_sum

def test_3x3():
    assert diagonal_sum([[1,2,3],[4,5,6],[7,8,9]]) == 15

def test_2x2():
    assert diagonal_sum([[1,2],[3,4]]) == 5

def test_1x1():
    assert diagonal_sum([[7]]) == 7
""".strip(),
)

T(
    "task_010", "off_by_one", "easy", 1,
    "caesar_cipher shifts by n-1 instead of n due to subtraction in modulo",
    buggy="""
def caesar_cipher(text, shift):
    result = []
    for ch in text:
        if ch.isalpha():
            base = ord('A') if ch.isupper() else ord('a')
            result.append(chr((ord(ch) - base + shift - 1) % 26 + base))
        else:
            result.append(ch)
    return ''.join(result)
""".strip(),
    fixed="""
def caesar_cipher(text, shift):
    result = []
    for ch in text:
        if ch.isalpha():
            base = ord('A') if ch.isupper() else ord('a')
            result.append(chr((ord(ch) - base + shift) % 26 + base))
        else:
            result.append(ch)
    return ''.join(result)
""".strip(),
    test="""
from solution import caesar_cipher

def test_shift3():
    assert caesar_cipher("abc", 3) == "def"

def test_shift1():
    assert caesar_cipher("z", 1) == "a"

def test_uppercase():
    assert caesar_cipher("ABC", 3) == "DEF"

def test_non_alpha():
    assert caesar_cipher("a b", 1) == "b c"

def test_shift26():
    assert caesar_cipher("abc", 26) == "abc"
""".strip(),
)

T(
    "task_011", "off_by_one", "medium", 1,
    "run_length_encoding starts count at 0 instead of 1",
    buggy="""
def run_length_encode(s):
    if not s:
        return ''
    result = []
    count = 0
    for i in range(len(s)):
        count += 1
        if i + 1 == len(s) or s[i] != s[i + 1]:
            result.append(f'{count}{s[i]}')
            count = 0
    return ''.join(result)
""".strip(),
    fixed="""
def run_length_encode(s):
    if not s:
        return ''
    result = []
    count = 1
    for i in range(1, len(s)):
        if s[i] == s[i - 1]:
            count += 1
        else:
            result.append(f'{count}{s[i-1]}')
            count = 1
    result.append(f'{count}{s[-1]}')
    return ''.join(result)
""".strip(),
    test="""
from solution import run_length_encode

def test_basic():
    assert run_length_encode("aabbbcc") == "2a3b2c"

def test_single():
    assert run_length_encode("a") == "1a"

def test_no_repeat():
    assert run_length_encode("abc") == "1a1b1c"

def test_all_same():
    assert run_length_encode("aaaa") == "4a"

def test_empty():
    assert run_length_encode("") == ""
""".strip(),
)

T(
    "task_012", "off_by_one", "medium", 1,
    "next_greater_element uses wrong start index in inner loop (starts at i instead of i+1)",
    buggy="""
def next_greater_element(arr):
    n = len(arr)
    result = [-1] * n
    for i in range(n):
        for j in range(i, n):
            if arr[j] > arr[i]:
                result[i] = arr[j]
                break
    return result
""".strip(),
    fixed="""
def next_greater_element(arr):
    n = len(arr)
    result = [-1] * n
    for i in range(n):
        for j in range(i + 1, n):
            if arr[j] > arr[i]:
                result[i] = arr[j]
                break
    return result
""".strip(),
    test="""
from solution import next_greater_element

def test_basic():
    assert next_greater_element([4, 5, 2, 10]) == [5, 10, 10, -1]

def test_descending():
    assert next_greater_element([5, 4, 3]) == [-1, -1, -1]

def test_single():
    assert next_greater_element([1]) == [-1]

def test_ascending():
    assert next_greater_element([1, 2, 3]) == [2, 3, -1]
""".strip(),
)

T(
    "task_013", "off_by_one", "easy", 1,
    "string_reverse iterates to len(s)//2 + 1, overwriting the middle of odd strings",
    buggy="""
def reverse_string(s):
    lst = list(s)
    n = len(lst)
    for i in range(n // 2 + 1):
        lst[i], lst[n - 1 - i] = lst[n - 1 - i], lst[i]
    return ''.join(lst)
""".strip(),
    fixed="""
def reverse_string(s):
    lst = list(s)
    n = len(lst)
    for i in range(n // 2):
        lst[i], lst[n - 1 - i] = lst[n - 1 - i], lst[i]
    return ''.join(lst)
""".strip(),
    test="""
from solution import reverse_string

def test_even():
    assert reverse_string("abcd") == "dcba"

def test_odd():
    assert reverse_string("abcde") == "edcba"

def test_single():
    assert reverse_string("a") == "a"

def test_two():
    assert reverse_string("ab") == "ba"

def test_palindrome():
    assert reverse_string("racecar") == "racecar"
""".strip(),
)

T(
    "task_014", "off_by_one", "medium", 1,
    "majority_element uses wrong threshold: n//2 instead of n//2 + 1 allowing non-majority",
    buggy="""
def majority_element(nums):
    n = len(nums)
    counts = {}
    for num in nums:
        counts[num] = counts.get(num, 0) + 1
        if counts[num] >= n // 2:
            return num
    return -1
""".strip(),
    fixed="""
def majority_element(nums):
    n = len(nums)
    counts = {}
    for num in nums:
        counts[num] = counts.get(num, 0) + 1
        if counts[num] > n // 2:
            return num
    return -1
""".strip(),
    test="""
from solution import majority_element

def test_clear_majority():
    assert majority_element([3, 2, 3]) == 3

def test_even_no_majority():
    # [1,1,2,2] -> no majority (each appears exactly n//2 times)
    assert majority_element([1, 1, 2, 2]) == -1

def test_all_same():
    assert majority_element([5, 5, 5]) == 5

def test_two_elements():
    assert majority_element([1, 1]) == 1
""".strip(),
)

T(
    "task_015", "off_by_one", "medium", 1,
    "trapping_rain_water starts from index 0 causing wrong left_max for first element",
    buggy="""
def trap_rain_water(height):
    n = len(height)
    if n < 3:
        return 0
    left_max = [0] * n
    right_max = [0] * n
    left_max[0] = height[0]
    for i in range(0, n):
        left_max[i] = max(left_max[i - 1], height[i])
    right_max[n - 1] = height[n - 1]
    for i in range(n - 2, -1, -1):
        right_max[i] = max(right_max[i + 1], height[i])
    water = 0
    for i in range(n):
        water += min(left_max[i], right_max[i]) - height[i]
    return water
""".strip(),
    fixed="""
def trap_rain_water(height):
    n = len(height)
    if n < 3:
        return 0
    left_max = [0] * n
    right_max = [0] * n
    left_max[0] = height[0]
    for i in range(1, n):
        left_max[i] = max(left_max[i - 1], height[i])
    right_max[n - 1] = height[n - 1]
    for i in range(n - 2, -1, -1):
        right_max[i] = max(right_max[i + 1], height[i])
    water = 0
    for i in range(n):
        water += min(left_max[i], right_max[i]) - height[i]
    return water
""".strip(),
    test="""
from solution import trap_rain_water

def test_basic():
    assert trap_rain_water([0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1]) == 6

def test_no_water():
    assert trap_rain_water([3, 2, 1]) == 0

def test_two_walls():
    assert trap_rain_water([3, 0, 3]) == 3

def test_short():
    assert trap_rain_water([1, 2]) == 0
""".strip(),
)

# ===========================================================================
# WRONG VARIABLE (12 tasks)
# ===========================================================================

T(
    "task_016", "wrong_variable", "easy", 1,
    "bubble_sort swaps arr[j] with arr[j] instead of arr[j+1]",
    buggy="""
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j] = arr[j + 1], arr[j]
    return arr
""".strip(),
    fixed="""
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr
""".strip(),
    test="""
from solution import bubble_sort

def test_basic():
    assert bubble_sort([64, 34, 25, 12, 22, 11, 90]) == [11, 12, 22, 25, 34, 64, 90]

def test_sorted():
    assert bubble_sort([1, 2, 3]) == [1, 2, 3]

def test_reverse():
    assert bubble_sort([3, 2, 1]) == [1, 2, 3]

def test_single():
    assert bubble_sort([1]) == [1]
""".strip(),
)

T(
    "task_017", "wrong_variable", "easy", 1,
    "gcd passes (a, b%a) instead of (b, a%b) causing infinite recursion or wrong result",
    buggy="""
def gcd(a, b):
    if b == 0:
        return a
    return gcd(a, b % a)
""".strip(),
    fixed="""
def gcd(a, b):
    if b == 0:
        return a
    return gcd(b, a % b)
""".strip(),
    test="""
from solution import gcd

def test_basic():
    assert gcd(48, 18) == 6

def test_coprime():
    assert gcd(7, 13) == 1

def test_same():
    assert gcd(5, 5) == 5

def test_one():
    assert gcd(1, 100) == 1

def test_multiples():
    assert gcd(100, 25) == 25
""".strip(),
)

T(
    "task_018", "wrong_variable", "easy", 1,
    "max_profit tracks max_price instead of min_price, never updates the buy signal correctly",
    buggy="""
def max_profit(prices):
    if not prices:
        return 0
    max_price = prices[0]
    profit = 0
    for price in prices[1:]:
        profit = max(profit, price - max_price)
        max_price = max(max_price, price)
    return profit
""".strip(),
    fixed="""
def max_profit(prices):
    if not prices:
        return 0
    min_price = prices[0]
    profit = 0
    for price in prices[1:]:
        profit = max(profit, price - min_price)
        min_price = min(min_price, price)
    return profit
""".strip(),
    test="""
from solution import max_profit

def test_basic():
    assert max_profit([7, 1, 5, 3, 6, 4]) == 5

def test_decreasing():
    assert max_profit([7, 6, 4, 3, 1]) == 0

def test_single():
    assert max_profit([5]) == 0

def test_two():
    assert max_profit([1, 5]) == 4
""".strip(),
)

T(
    "task_019", "wrong_variable", "easy", 1,
    "string_compression appends char before count, producing reversed encoding",
    buggy="""
def compress_string(s):
    if not s:
        return ''
    result = []
    count = 1
    for i in range(1, len(s)):
        if s[i] == s[i - 1]:
            count += 1
        else:
            result.append(s[i] + str(count))
            count = 1
    result.append(s[-1] + str(count))
    return ''.join(result)
""".strip(),
    fixed="""
def compress_string(s):
    if not s:
        return ''
    result = []
    count = 1
    for i in range(1, len(s)):
        if s[i] == s[i - 1]:
            count += 1
        else:
            result.append(s[i - 1] + str(count))
            count = 1
    result.append(s[-1] + str(count))
    return ''.join(result)
""".strip(),
    test="""
from solution import compress_string

def test_basic():
    assert compress_string("aabbbcc") == "a2b3c2"

def test_no_compress():
    assert compress_string("abc") == "a1b1c1"

def test_all_same():
    assert compress_string("aaaa") == "a4"

def test_single():
    assert compress_string("x") == "x1"
""".strip(),
)

T(
    "task_020", "wrong_variable", "easy", 1,
    "find_second_largest returns largest instead of second largest",
    buggy="""
def find_second_largest(nums):
    first = second = float('-inf')
    for num in nums:
        if num > first:
            second = first
            first = num
        elif num > second and num != first:
            second = num
    return first
""".strip(),
    fixed="""
def find_second_largest(nums):
    first = second = float('-inf')
    for num in nums:
        if num > first:
            second = first
            first = num
        elif num > second and num != first:
            second = num
    return second
""".strip(),
    test="""
from solution import find_second_largest

def test_basic():
    assert find_second_largest([3, 1, 4, 1, 5, 9, 2, 6]) == 6

def test_two_elements():
    assert find_second_largest([10, 5]) == 5

def test_negatives():
    assert find_second_largest([-1, -2, -3]) == -2

def test_three():
    assert find_second_largest([1, 2, 3]) == 2
""".strip(),
)

T(
    "task_021", "wrong_variable", "medium", 1,
    "valid_anagram decrements counter for s instead of t for t's characters",
    buggy="""
def is_anagram(s, t):
    if len(s) != len(t):
        return False
    counts = {}
    for ch in s:
        counts[ch] = counts.get(ch, 0) + 1
    for ch in t:
        counts[ch] = counts.get(ch, 0) - 1
    return all(v == 0 for v in counts.values())
""".strip(),
    fixed="""
def is_anagram(s, t):
    if len(s) != len(t):
        return False
    counts = {}
    for ch in s:
        counts[ch] = counts.get(ch, 0) + 1
    for ch in t:
        if ch not in counts:
            return False
        counts[ch] -= 1
    return all(v == 0 for v in counts.values())
""".strip(),
    test="""
from solution import is_anagram

def test_anagram():
    assert is_anagram("anagram", "nagaram") is True

def test_not_anagram():
    assert is_anagram("rat", "car") is False

def test_different_chars():
    assert is_anagram("abc", "abd") is False

def test_same():
    assert is_anagram("a", "a") is True
""".strip(),
)

T(
    "task_022", "wrong_variable", "easy", 1,
    "word_count uses wrong variable name, counting chars instead of words",
    buggy="""
def word_count(sentence):
    counts = {}
    for word in sentence.split():
        counts[sentence] = counts.get(sentence, 0) + 1
    return counts
""".strip(),
    fixed="""
def word_count(sentence):
    counts = {}
    for word in sentence.split():
        counts[word] = counts.get(word, 0) + 1
    return counts
""".strip(),
    test="""
from solution import word_count

def test_basic():
    assert word_count("hello world hello") == {"hello": 2, "world": 1}

def test_single():
    assert word_count("one") == {"one": 1}

def test_multiple():
    result = word_count("a b a c a")
    assert result == {"a": 3, "b": 1, "c": 1}
""".strip(),
)

T(
    "task_023", "wrong_variable", "easy", 1,
    "transpose_matrix swaps matrix[i][j] with matrix[i][j] (no-op) instead of matrix[j][i]",
    buggy="""
def transpose(matrix):
    n = len(matrix)
    for i in range(n):
        for j in range(i + 1, n):
            matrix[i][j], matrix[i][j] = matrix[j][i], matrix[i][j]
    return matrix
""".strip(),
    fixed="""
def transpose(matrix):
    n = len(matrix)
    for i in range(n):
        for j in range(i + 1, n):
            matrix[i][j], matrix[j][i] = matrix[j][i], matrix[i][j]
    return matrix
""".strip(),
    test="""
from solution import transpose

def test_2x2():
    assert transpose([[1,2],[3,4]]) == [[1,3],[2,4]]

def test_3x3():
    m = [[1,2,3],[4,5,6],[7,8,9]]
    assert transpose(m) == [[1,4,7],[2,5,8],[3,6,9]]

def test_identity():
    assert transpose([[1,0],[0,1]]) == [[1,0],[0,1]]
""".strip(),
)

T(
    "task_024", "wrong_variable", "easy", 1,
    "capitalize_words calls lower() instead of capitalize() on each word",
    buggy="""
def capitalize_words(sentence):
    return ' '.join(word.lower() for word in sentence.split())
""".strip(),
    fixed="""
def capitalize_words(sentence):
    return ' '.join(word.capitalize() for word in sentence.split())
""".strip(),
    test="""
from solution import capitalize_words

def test_basic():
    assert capitalize_words("hello world") == "Hello World"

def test_already():
    assert capitalize_words("Python Is Great") == "Python Is Great"

def test_lower():
    assert capitalize_words("foo bar baz") == "Foo Bar Baz"
""".strip(),
)

T(
    "task_025", "wrong_variable", "medium", 1,
    "power function passes exponent as base and base as exponent",
    buggy="""
def power(base, exponent):
    result = 1
    for _ in range(base):
        result *= exponent
    return result
""".strip(),
    fixed="""
def power(base, exponent):
    result = 1
    for _ in range(exponent):
        result *= base
    return result
""".strip(),
    test="""
from solution import power

def test_basic():
    assert power(2, 3) == 8

def test_one():
    assert power(5, 1) == 5

def test_zero_exp():
    assert power(7, 0) == 1

def test_ten():
    assert power(10, 2) == 100
""".strip(),
)

T(
    "task_026", "wrong_variable", "easy", 1,
    "count_vowels checks character against consonants set instead of vowels set",
    buggy="""
def count_vowels(s):
    consonants = set('bcdfghjklmnpqrstvwxyz')
    return sum(1 for ch in s.lower() if ch in consonants)
""".strip(),
    fixed="""
def count_vowels(s):
    vowels = set('aeiou')
    return sum(1 for ch in s.lower() if ch in vowels)
""".strip(),
    test="""
from solution import count_vowels

def test_basic():
    assert count_vowels("hello") == 2

def test_none():
    assert count_vowels("sky") == 0

def test_all_vowels():
    assert count_vowels("aeiou") == 5

def test_mixed():
    assert count_vowels("Python") == 1
""".strip(),
)

T(
    "task_027", "wrong_variable", "medium", 1,
    "longest_common_prefix compares prefix against second string instead of third, giving wrong result",
    buggy="""
def longest_common_prefix(strs):
    if not strs:
        return ''
    prefix = strs[0]
    for s in strs[1:]:
        while not prefix.startswith(s[:len(prefix)]):
            prefix = prefix[:-1]
            if not prefix:
                return ''
    return prefix
""".strip(),
    fixed="""
def longest_common_prefix(strs):
    if not strs:
        return ''
    prefix = strs[0]
    for s in strs[1:]:
        while not s.startswith(prefix):
            prefix = prefix[:-1]
            if not prefix:
                return ''
    return prefix
""".strip(),
    test="""
from solution import longest_common_prefix

def test_basic():
    assert longest_common_prefix(["flower", "flow", "flight"]) == "fl"

def test_none():
    assert longest_common_prefix(["dog", "racecar", "car"]) == ""

def test_one():
    assert longest_common_prefix(["alone"]) == "alone"

def test_same():
    assert longest_common_prefix(["abc", "abc"]) == "abc"
""".strip(),
)

# ===========================================================================
# MISSING CHECK (15 tasks)
# ===========================================================================

T(
    "task_028", "missing_check", "easy", 2,
    "safe_divide raises ZeroDivisionError because it doesn't check for zero denominator",
    buggy="""
def safe_divide(a, b):
    return a / b
""".strip(),
    fixed="""
def safe_divide(a, b):
    if b == 0:
        return None
    return a / b
""".strip(),
    test="""
from solution import safe_divide

def test_normal():
    assert safe_divide(10, 2) == 5.0

def test_zero_denominator():
    assert safe_divide(5, 0) is None

def test_negative():
    assert safe_divide(-6, 3) == -2.0

def test_float():
    assert safe_divide(1, 4) == 0.25
""".strip(),
)

T(
    "task_029", "missing_check", "easy", 2,
    "list_average raises ZeroDivisionError on empty list instead of returning None",
    buggy="""
def list_average(nums):
    return sum(nums) / len(nums)
""".strip(),
    fixed="""
def list_average(nums):
    if not nums:
        return None
    return sum(nums) / len(nums)
""".strip(),
    test="""
from solution import list_average

def test_basic():
    assert list_average([1, 2, 3, 4]) == 2.5

def test_empty():
    assert list_average([]) is None

def test_single():
    assert list_average([5]) == 5.0

def test_negative():
    assert list_average([-1, 1]) == 0.0
""".strip(),
)

T(
    "task_030", "missing_check", "easy", 3,
    "safe_sqrt raises ValueError on negative input instead of returning None",
    buggy="""
import math

def safe_sqrt(n):
    return math.sqrt(n)
""".strip(),
    fixed="""
import math

def safe_sqrt(n):
    if n < 0:
        return None
    return math.sqrt(n)
""".strip(),
    test="""
from solution import safe_sqrt

def test_positive():
    assert safe_sqrt(4) == 2.0

def test_zero():
    assert safe_sqrt(0) == 0.0

def test_negative():
    assert safe_sqrt(-1) is None

def test_float():
    import math
    assert math.isclose(safe_sqrt(2), math.sqrt(2))
""".strip(),
)

T(
    "task_031", "missing_check", "easy", 3,
    "stack_peek raises IndexError on empty stack instead of returning None",
    buggy="""
def stack_peek(stack):
    return stack[-1]
""".strip(),
    fixed="""
def stack_peek(stack):
    if not stack:
        return None
    return stack[-1]
""".strip(),
    test="""
from solution import stack_peek

def test_normal():
    assert stack_peek([1, 2, 3]) == 3

def test_empty():
    assert stack_peek([]) is None

def test_single():
    assert stack_peek([42]) == 42
""".strip(),
)

T(
    "task_032", "missing_check", "easy", 2,
    "is_prime returns True for n=1, which is not a prime number",
    buggy="""
def is_prime(n):
    if n < 2:
        return True
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True
""".strip(),
    fixed="""
def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True
""".strip(),
    test="""
from solution import is_prime

def test_prime():
    assert is_prime(7) is True

def test_not_prime():
    assert is_prime(9) is False

def test_one():
    assert is_prime(1) is False

def test_zero():
    assert is_prime(0) is False

def test_two():
    assert is_prime(2) is True

def test_large():
    assert is_prime(97) is True
""".strip(),
)

T(
    "task_033", "missing_check", "easy", 3,
    "factorial doesn't handle n=0, returning wrong result due to empty range",
    buggy="""
def factorial(n):
    result = 0
    for i in range(1, n + 1):
        result *= i
    return result
""".strip(),
    fixed="""
def factorial(n):
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result
""".strip(),
    test="""
from solution import factorial

def test_zero():
    assert factorial(0) == 1

def test_one():
    assert factorial(1) == 1

def test_five():
    assert factorial(5) == 120

def test_ten():
    assert factorial(10) == 3628800
""".strip(),
)

T(
    "task_034", "missing_check", "medium", 3,
    "count_digits returns 0 for n=0 instead of 1",
    buggy="""
def count_digits(n):
    n = abs(n)
    count = 0
    while n > 0:
        n //= 10
        count += 1
    return count
""".strip(),
    fixed="""
def count_digits(n):
    n = abs(n)
    if n == 0:
        return 1
    count = 0
    while n > 0:
        n //= 10
        count += 1
    return count
""".strip(),
    test="""
from solution import count_digits

def test_zero():
    assert count_digits(0) == 1

def test_single():
    assert count_digits(5) == 1

def test_two():
    assert count_digits(42) == 2

def test_negative():
    assert count_digits(-123) == 3
""".strip(),
)

T(
    "task_035", "missing_check", "easy", 3,
    "first_element raises IndexError on empty list instead of returning None",
    buggy="""
def first_element(lst):
    return lst[0]
""".strip(),
    fixed="""
def first_element(lst):
    if not lst:
        return None
    return lst[0]
""".strip(),
    test="""
from solution import first_element

def test_normal():
    assert first_element([1, 2, 3]) == 1

def test_empty():
    assert first_element([]) is None

def test_single():
    assert first_element([99]) == 99
""".strip(),
)

T(
    "task_036", "missing_check", "medium", 3,
    "max_in_matrix crashes on empty matrix instead of returning None",
    buggy="""
def max_in_matrix(matrix):
    return max(max(row) for row in matrix)
""".strip(),
    fixed="""
def max_in_matrix(matrix):
    if not matrix or not matrix[0]:
        return None
    return max(max(row) for row in matrix)
""".strip(),
    test="""
from solution import max_in_matrix

def test_basic():
    assert max_in_matrix([[1,2],[3,4]]) == 4

def test_empty():
    assert max_in_matrix([]) is None

def test_single():
    assert max_in_matrix([[7]]) == 7

def test_negatives():
    assert max_in_matrix([[-5, -3], [-10, -1]]) == -1
""".strip(),
)

T(
    "task_037", "missing_check", "easy", 2,
    "remove_item raises ValueError when item not in list instead of returning list unchanged",
    buggy="""
def remove_item(lst, item):
    lst = list(lst)
    lst.remove(item)
    return lst
""".strip(),
    fixed="""
def remove_item(lst, item):
    lst = list(lst)
    if item in lst:
        lst.remove(item)
    return lst
""".strip(),
    test="""
from solution import remove_item

def test_found():
    assert remove_item([1, 2, 3], 2) == [1, 3]

def test_not_found():
    assert remove_item([1, 2, 3], 5) == [1, 2, 3]

def test_empty():
    assert remove_item([], 1) == []
""".strip(),
)

T(
    "task_038", "missing_check", "easy", 3,
    "merge_sorted_lists doesn't handle empty list inputs correctly",
    buggy="""
def merge_sorted(a, b):
    result = []
    i = j = 0
    while i < len(a) and j < len(b):
        if a[i] <= b[j]:
            result.append(a[i])
            i += 1
        else:
            result.append(b[j])
            j += 1
    result.extend(a[i:])
    result.extend(b[j:])
    return result
""".strip(),
    fixed="""
def merge_sorted(a, b):
    result = []
    i = j = 0
    while i < len(a) and j < len(b):
        if a[i] <= b[j]:
            result.append(a[i])
            i += 1
        else:
            result.append(b[j])
            j += 1
    result.extend(a[i:])
    result.extend(b[j:])
    return result
""".strip(),
    test="""
from solution import merge_sorted

def test_basic():
    assert merge_sorted([1, 3, 5], [2, 4, 6]) == [1, 2, 3, 4, 5, 6]

def test_first_empty():
    assert merge_sorted([], [1, 2]) == [1, 2]

def test_second_empty():
    assert merge_sorted([1, 2], []) == [1, 2]

def test_both_empty():
    assert merge_sorted([], []) == []
""".strip(),
)

# This one is actually correct. Let me replace with a real bug.
TASKS.pop()

T(
    "task_038", "missing_check", "medium", 2,
    "binary_search_empty crashes with IndexError on empty list instead of returning -1",
    buggy="""
def binary_search_safe(arr, target):
    low, high = 0, len(arr) - 1
    while low <= high:
        mid = (low + high) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1
""".strip(),
    fixed="""
def binary_search_safe(arr, target):
    if not arr:
        return -1
    low, high = 0, len(arr) - 1
    while low <= high:
        mid = (low + high) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1
""".strip(),
    test="""
from solution import binary_search_safe

def test_found():
    assert binary_search_safe([1, 3, 5], 3) == 1

def test_empty():
    # buggy version: low=0, high=-1, loop doesn't execute, returns -1 correctly
    # Actually the bug is different - with empty arr, len(arr)-1 = -1, loop skips
    # Let's test the specific guaranteed behavior
    assert binary_search_safe([], 5) == -1

def test_not_found():
    assert binary_search_safe([1, 2, 3], 4) == -1

def test_single_found():
    assert binary_search_safe([7], 7) == 0
""".strip(),
)

# Hmm, the binary_search_safe bug doesn't actually crash. Let me use a genuine one.
TASKS.pop()

T(
    "task_038", "missing_check", "easy", 2,
    "safe_log raises ValueError on non-positive input instead of returning None",
    buggy="""
import math

def safe_log(n):
    return math.log(n)
""".strip(),
    fixed="""
import math

def safe_log(n):
    if n <= 0:
        return None
    return math.log(n)
""".strip(),
    test="""
from solution import safe_log

def test_positive():
    import math
    assert math.isclose(safe_log(math.e), 1.0)

def test_zero():
    assert safe_log(0) is None

def test_negative():
    assert safe_log(-5) is None

def test_one():
    assert safe_log(1) == 0.0
""".strip(),
)

T(
    "task_039", "missing_check", "medium", 2,
    "nested_list_depth misses empty list base case, returning 1 instead of 0",
    buggy="""
def list_depth(lst):
    if not isinstance(lst, list):
        return 0
    return 1 + max(list_depth(item) for item in lst)
""".strip(),
    fixed="""
def list_depth(lst):
    if not isinstance(lst, list):
        return 0
    if not lst:
        return 1
    return 1 + max(list_depth(item) for item in lst)
""".strip(),
    test="""
from solution import list_depth

def test_flat():
    assert list_depth([1, 2, 3]) == 1

def test_nested():
    assert list_depth([1, [2, [3]]]) == 3

def test_empty():
    assert list_depth([]) == 1

def test_scalar():
    assert list_depth(5) == 0
""".strip(),
)

T(
    "task_040", "missing_check", "easy", 2,
    "safe_pop raises IndexError on empty list instead of returning None",
    buggy="""
def safe_pop(lst):
    return lst.pop()
""".strip(),
    fixed="""
def safe_pop(lst):
    if not lst:
        return None
    return lst.pop()
""".strip(),
    test="""
from solution import safe_pop

def test_normal():
    lst = [1, 2, 3]
    assert safe_pop(lst) == 3

def test_empty():
    assert safe_pop([]) is None

def test_single():
    lst = [42]
    assert safe_pop(lst) == 42
    assert lst == []
""".strip(),
)

T(
    "task_041", "missing_check", "easy", 3,
    "count_words returns 1 for empty string instead of 0",
    buggy="""
def count_words(sentence):
    return len(sentence.split())
""".strip(),
    fixed="""
def count_words(sentence):
    if not sentence or not sentence.strip():
        return 0
    return len(sentence.split())
""".strip(),
    test="""
from solution import count_words

def test_basic():
    assert count_words("hello world") == 2

def test_empty():
    assert count_words("") == 0

def test_spaces():
    assert count_words("   ") == 0

def test_one():
    assert count_words("hello") == 1
""".strip(),
)

# task_041 is actually correct in the buggy version too. Let me use real code.
TASKS.pop()

T(
    "task_041", "missing_check", "easy", 2,
    "dict_get raises KeyError when key is missing instead of returning a default value",
    buggy="""
def safe_dict_get(d, key, default=None):
    return d[key]
""".strip(),
    fixed="""
def safe_dict_get(d, key, default=None):
    return d.get(key, default)
""".strip(),
    test="""
from solution import safe_dict_get

def test_found():
    assert safe_dict_get({"a": 1}, "a") == 1

def test_missing():
    assert safe_dict_get({"a": 1}, "b") is None

def test_default():
    assert safe_dict_get({"a": 1}, "b", 42) == 42
""".strip(),
)

T(
    "task_042", "missing_check", "medium", 2,
    "flatten_list crashes with RecursionError on deeply nested empty lists",
    buggy="""
def flatten(lst):
    result = []
    for item in lst:
        if isinstance(item, list):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result
""".strip(),
    fixed="""
def flatten(lst):
    result = []
    for item in lst:
        if isinstance(item, list):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result
""".strip(),
    test="""
from solution import flatten

def test_nested():
    assert flatten([1, [2, [3, [4]]]]) == [1, 2, 3, 4]

def test_flat():
    assert flatten([1, 2, 3]) == [1, 2, 3]

def test_empty():
    assert flatten([]) == []

def test_mixed():
    assert flatten([1, [2, 3], [4, [5]]]) == [1, 2, 3, 4, 5]
""".strip(),
)

# This one is correct. Replace with actual bug.
TASKS.pop()

T(
    "task_042", "missing_check", "easy", 2,
    "string_to_int crashes on whitespace input due to missing strip() call",
    buggy="""
def parse_int(s):
    return int(s)
""".strip(),
    fixed="""
def parse_int(s):
    return int(s.strip())
""".strip(),
    test="""
from solution import parse_int

def test_normal():
    assert parse_int("42") == 42

def test_leading_space():
    assert parse_int("  42") == 42

def test_trailing_space():
    assert parse_int("42  ") == 42

def test_both_spaces():
    assert parse_int("  -5  ") == -5
""".strip(),
)

# ===========================================================================
# LOGIC ERROR (18 tasks)
# ===========================================================================

T(
    "task_043", "logic_error", "easy", 1,
    "max_subarray uses min() instead of max() to update the running maximum",
    buggy="""
def max_subarray(nums):
    max_sum = current = nums[0]
    for num in nums[1:]:
        current = min(current + num, num)
        max_sum = max(max_sum, current)
    return max_sum
""".strip(),
    fixed="""
def max_subarray(nums):
    max_sum = current = nums[0]
    for num in nums[1:]:
        current = max(current + num, num)
        max_sum = max(max_sum, current)
    return max_sum
""".strip(),
    test="""
from solution import max_subarray

def test_basic():
    assert max_subarray([-2, 1, -3, 4, -1, 2, 1, -5, 4]) == 6

def test_all_negative():
    assert max_subarray([-1, -2, -3]) == -1

def test_all_positive():
    assert max_subarray([1, 2, 3]) == 6

def test_single():
    assert max_subarray([5]) == 5
""".strip(),
)

T(
    "task_044", "logic_error", "easy", 1,
    "check_sorted uses strict < allowing equal consecutive elements to fail",
    buggy="""
def is_non_decreasing(arr):
    for i in range(len(arr) - 1):
        if arr[i] > arr[i + 1]:
            return False
    return True
""".strip(),
    fixed="""
def is_non_decreasing(arr):
    for i in range(len(arr) - 1):
        if arr[i] > arr[i + 1]:
            return False
    return True
""".strip(),
    test="""
from solution import is_non_decreasing

def test_sorted():
    assert is_non_decreasing([1, 2, 3]) is True

def test_equal_elements():
    assert is_non_decreasing([1, 1, 2]) is True

def test_unsorted():
    assert is_non_decreasing([3, 1, 2]) is False

def test_single():
    assert is_non_decreasing([1]) is True
""".strip(),
)

# This one is correct. Replace.
TASKS.pop()

T(
    "task_044", "logic_error", "easy", 1,
    "is_sorted returns False for arrays with equal consecutive elements due to wrong operator",
    buggy="""
def is_sorted(arr):
    for i in range(len(arr) - 1):
        if arr[i] >= arr[i + 1]:
            return False
    return True
""".strip(),
    fixed="""
def is_sorted(arr):
    for i in range(len(arr) - 1):
        if arr[i] > arr[i + 1]:
            return False
    return True
""".strip(),
    test="""
from solution import is_sorted

def test_sorted():
    assert is_sorted([1, 2, 3]) is True

def test_equal_consecutive():
    assert is_sorted([1, 1, 2]) is True

def test_unsorted():
    assert is_sorted([2, 1]) is False

def test_empty():
    assert is_sorted([]) is True
""".strip(),
)

T(
    "task_045", "logic_error", "easy", 1,
    "count_evens checks odd condition instead of even condition",
    buggy="""
def count_evens(nums):
    return sum(1 for n in nums if n % 2 != 0)
""".strip(),
    fixed="""
def count_evens(nums):
    return sum(1 for n in nums if n % 2 == 0)
""".strip(),
    test="""
from solution import count_evens

def test_basic():
    assert count_evens([1, 2, 3, 4, 5]) == 2

def test_all_even():
    assert count_evens([2, 4, 6]) == 3

def test_all_odd():
    assert count_evens([1, 3, 5]) == 0

def test_empty():
    assert count_evens([]) == 0
""".strip(),
)

T(
    "task_046", "logic_error", "easy", 1,
    "factorial uses addition instead of multiplication",
    buggy="""
def factorial(n):
    result = 1
    for i in range(1, n + 1):
        result += i
    return result
""".strip(),
    fixed="""
def factorial(n):
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result
""".strip(),
    test="""
from solution import factorial

def test_zero():
    assert factorial(0) == 1

def test_one():
    assert factorial(1) == 1

def test_five():
    assert factorial(5) == 120

def test_six():
    assert factorial(6) == 720
""".strip(),
)

T(
    "task_047", "logic_error", "easy", 1,
    "sum_of_squares sums then squares instead of squaring each element then summing",
    buggy="""
def sum_of_squares(nums):
    return sum(nums) ** 2
""".strip(),
    fixed="""
def sum_of_squares(nums):
    return sum(n ** 2 for n in nums)
""".strip(),
    test="""
from solution import sum_of_squares

def test_basic():
    assert sum_of_squares([1, 2, 3]) == 14

def test_single():
    assert sum_of_squares([4]) == 16

def test_zeros():
    assert sum_of_squares([0, 0]) == 0
""".strip(),
)

T(
    "task_048", "logic_error", "medium", 1,
    "is_palindrome doesn't lowercase before comparing, failing on mixed-case palindromes",
    buggy="""
def is_palindrome(s):
    cleaned = ''.join(ch for ch in s if ch.isalnum())
    return cleaned == cleaned[::-1]
""".strip(),
    fixed="""
def is_palindrome(s):
    cleaned = ''.join(ch.lower() for ch in s if ch.isalnum())
    return cleaned == cleaned[::-1]
""".strip(),
    test="""
from solution import is_palindrome

def test_lower():
    assert is_palindrome("racecar") is True

def test_mixed_case():
    assert is_palindrome("Racecar") is True

def test_phrase():
    assert is_palindrome("A man a plan a canal Panama") is True

def test_not():
    assert is_palindrome("hello") is False
""".strip(),
)

T(
    "task_049", "logic_error", "easy", 1,
    "find_max initializes max_val to 0, failing for all-negative arrays",
    buggy="""
def find_max(nums):
    max_val = 0
    for num in nums:
        if num > max_val:
            max_val = num
    return max_val
""".strip(),
    fixed="""
def find_max(nums):
    max_val = nums[0]
    for num in nums[1:]:
        if num > max_val:
            max_val = num
    return max_val
""".strip(),
    test="""
from solution import find_max

def test_basic():
    assert find_max([3, 1, 4, 1, 5, 9, 2, 6]) == 9

def test_all_negative():
    assert find_max([-5, -1, -3]) == -1

def test_single():
    assert find_max([7]) == 7

def test_negatives_and_positives():
    assert find_max([-10, 5, 3]) == 5
""".strip(),
)

T(
    "task_050", "logic_error", "easy", 1,
    "find_min initializes min_val to 0 instead of first element, failing for all-positive arrays > 0",
    buggy="""
def find_min(nums):
    min_val = 0
    for num in nums:
        if num < min_val:
            min_val = num
    return min_val
""".strip(),
    fixed="""
def find_min(nums):
    min_val = nums[0]
    for num in nums[1:]:
        if num < min_val:
            min_val = num
    return min_val
""".strip(),
    test="""
from solution import find_min

def test_basic():
    assert find_min([3, 1, 4, 1, 5]) == 1

def test_all_positive():
    assert find_min([5, 3, 7]) == 3

def test_all_negative():
    assert find_min([-1, -5, -2]) == -5

def test_single():
    assert find_min([42]) == 42
""".strip(),
)

T(
    "task_051", "logic_error", "medium", 1,
    "fizzbuzz checks multiples of 3 and 5 before checking 15, missing FizzBuzz output",
    buggy="""
def fizzbuzz(n):
    result = []
    for i in range(1, n + 1):
        if i % 3 == 0:
            result.append('Fizz')
        elif i % 5 == 0:
            result.append('Buzz')
        elif i % 15 == 0:
            result.append('FizzBuzz')
        else:
            result.append(str(i))
    return result
""".strip(),
    fixed="""
def fizzbuzz(n):
    result = []
    for i in range(1, n + 1):
        if i % 15 == 0:
            result.append('FizzBuzz')
        elif i % 3 == 0:
            result.append('Fizz')
        elif i % 5 == 0:
            result.append('Buzz')
        else:
            result.append(str(i))
    return result
""".strip(),
    test="""
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
""".strip(),
)

T(
    "task_052", "logic_error", "easy", 1,
    "remove_vowels keeps vowels and removes consonants due to inverted condition",
    buggy="""
def remove_vowels(s):
    vowels = set('aeiouAEIOU')
    return ''.join(ch for ch in s if ch in vowels)
""".strip(),
    fixed="""
def remove_vowels(s):
    vowels = set('aeiouAEIOU')
    return ''.join(ch for ch in s if ch not in vowels)
""".strip(),
    test="""
from solution import remove_vowels

def test_basic():
    assert remove_vowels("hello") == "hll"

def test_all_vowels():
    assert remove_vowels("aeiou") == ""

def test_no_vowels():
    assert remove_vowels("rhythm") == "rhythm"

def test_mixed():
    assert remove_vowels("Python") == "Pythn"
""".strip(),
)

T(
    "task_053", "logic_error", "easy", 1,
    "frequency_count uses != instead of == when counting target, counting everything else",
    buggy="""
def count_occurrences(lst, target):
    return sum(1 for item in lst if item != target)
""".strip(),
    fixed="""
def count_occurrences(lst, target):
    return sum(1 for item in lst if item == target)
""".strip(),
    test="""
from solution import count_occurrences

def test_basic():
    assert count_occurrences([1, 2, 2, 3, 2], 2) == 3

def test_none():
    assert count_occurrences([1, 2, 3], 5) == 0

def test_all():
    assert count_occurrences([4, 4, 4], 4) == 3
""".strip(),
)

T(
    "task_054", "logic_error", "medium", 1,
    "check_balanced uses wrong counter update: increments for ) and decrements for (",
    buggy="""
def is_balanced(s):
    count = 0
    for ch in s:
        if ch == ')':
            count += 1
        elif ch == '(':
            count -= 1
        if count < 0:
            return False
    return count == 0
""".strip(),
    fixed="""
def is_balanced(s):
    count = 0
    for ch in s:
        if ch == '(':
            count += 1
        elif ch == ')':
            count -= 1
        if count < 0:
            return False
    return count == 0
""".strip(),
    test="""
from solution import is_balanced

def test_balanced():
    assert is_balanced("(())") is True

def test_unbalanced():
    assert is_balanced("(()") is False

def test_empty():
    assert is_balanced("") is True

def test_simple():
    assert is_balanced("()") is True

def test_wrong_order():
    assert is_balanced(")(") is False
""".strip(),
)

T(
    "task_055", "logic_error", "medium", 1,
    "gcd_by_subtraction subtracts wrong way: does a-b instead of b%a, looping forever for some inputs",
    buggy="""
def gcd_sub(a, b):
    while a != b:
        if a > b:
            a = a - b
        else:
            a = b - a
    return a
""".strip(),
    fixed="""
def gcd_sub(a, b):
    while a != b:
        if a > b:
            a = a - b
        else:
            b = b - a
    return a
""".strip(),
    test="""
from solution import gcd_sub

def test_basic():
    assert gcd_sub(48, 18) == 6

def test_coprime():
    assert gcd_sub(7, 3) == 1

def test_same():
    assert gcd_sub(5, 5) == 5

def test_multiples():
    assert gcd_sub(12, 4) == 4
""".strip(),
)

T(
    "task_056", "logic_error", "easy", 1,
    "binary_to_decimal uses + instead of | (bitwise OR), giving wrong results",
    buggy="""
def binary_to_decimal(binary_str):
    result = 0
    for bit in binary_str:
        result = result * 2 + int(bit)
    return result
""".strip(),
    fixed="""
def binary_to_decimal(binary_str):
    result = 0
    for bit in binary_str:
        result = (result << 1) | int(bit)
    return result
""".strip(),
    test="""
from solution import binary_to_decimal

def test_basic():
    assert binary_to_decimal("1010") == 10

def test_one():
    assert binary_to_decimal("1") == 1

def test_zero():
    assert binary_to_decimal("0") == 0

def test_eight():
    assert binary_to_decimal("1000") == 8

def test_fifteen():
    assert binary_to_decimal("1111") == 15
""".strip(),
)

# task_056 is correct in both. Let me replace with something different.
TASKS.pop()

T(
    "task_056", "logic_error", "easy", 1,
    "sort_by_length sorts by negative length, giving descending order instead of ascending",
    buggy="""
def sort_by_length(words):
    return sorted(words, key=lambda w: -len(w))
""".strip(),
    fixed="""
def sort_by_length(words):
    return sorted(words, key=len)
""".strip(),
    test="""
from solution import sort_by_length

def test_basic():
    assert sort_by_length(["banana", "apple", "fig", "cherry"]) == ["fig", "apple", "banana", "cherry"]

def test_equal():
    result = sort_by_length(["ab", "cd"])
    assert len(result[0]) <= len(result[1])

def test_single():
    assert sort_by_length(["hello"]) == ["hello"]
""".strip(),
)

T(
    "task_057", "logic_error", "medium", 1,
    "two_sum uses wrong condition, finding same element twice instead of two different elements",
    buggy="""
def two_sum_exists(nums, target):
    for i in range(len(nums)):
        for j in range(len(nums)):
            if i != j and nums[i] + nums[j] == target:
                return True
    return False
""".strip(),
    fixed="""
def two_sum_exists(nums, target):
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return True
    return False
""".strip(),
    test="""
from solution import two_sum_exists

def test_found():
    assert two_sum_exists([2, 7, 11, 15], 9) is True

def test_not_found():
    assert two_sum_exists([1, 2, 3], 10) is False

def test_single_element():
    # target = 2*nums[0] should NOT be found if there's only one such element
    assert two_sum_exists([5], 10) is False

def test_two_elements():
    assert two_sum_exists([3, 7], 10) is True
""".strip(),
)

T(
    "task_058", "logic_error", "medium", 1,
    "flatten_recursive uses wrong base case condition, not flattening properly",
    buggy="""
def flatten(lst):
    if not isinstance(lst, list) or len(lst) == 0:
        return [lst] if lst else []
    return flatten(lst[0]) + flatten(lst[1:])
""".strip(),
    fixed="""
def flatten(lst):
    if not isinstance(lst, list):
        return [lst]
    if not lst:
        return []
    return flatten(lst[0]) + flatten(lst[1:])
""".strip(),
    test="""
from solution import flatten

def test_basic():
    assert flatten([1, [2, 3], [4, [5]]]) == [1, 2, 3, 4, 5]

def test_flat():
    assert flatten([1, 2, 3]) == [1, 2, 3]

def test_empty():
    assert flatten([]) == []

def test_deep():
    assert flatten([[[1]], [2, [3]]]) == [1, 2, 3]
""".strip(),
)

T(
    "task_059", "logic_error", "easy", 1,
    "and_or_confusion: uses 'and' where 'or' is needed in leap year check",
    buggy="""
def is_leap_year(year):
    return (year % 4 == 0 and year % 100 != 0) and (year % 400 == 0)
""".strip(),
    fixed="""
def is_leap_year(year):
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
""".strip(),
    test="""
from solution import is_leap_year

def test_400():
    assert is_leap_year(2000) is True

def test_100():
    assert is_leap_year(1900) is False

def test_4():
    assert is_leap_year(2024) is True

def test_not_leap():
    assert is_leap_year(2023) is False
""".strip(),
)

T(
    "task_060", "logic_error", "easy", 1,
    "product_of_list uses sum() instead of computing the product",
    buggy="""
def product_of_list(nums):
    result = 0
    for n in nums:
        result += n
    return result
""".strip(),
    fixed="""
def product_of_list(nums):
    result = 1
    for n in nums:
        result *= n
    return result
""".strip(),
    test="""
from solution import product_of_list

def test_basic():
    assert product_of_list([1, 2, 3, 4]) == 24

def test_single():
    assert product_of_list([5]) == 5

def test_with_zero():
    assert product_of_list([1, 2, 0, 4]) == 0

def test_negatives():
    assert product_of_list([-1, -2, 3]) == 6
""".strip(),
)

# ===========================================================================
# TYPE ERROR (10 tasks)
# ===========================================================================

T(
    "task_061", "type_error", "easy", 1,
    "join_numbers fails with TypeError trying to join integers without converting to strings",
    buggy="""
def join_numbers(nums, sep=', '):
    return sep.join(nums)
""".strip(),
    fixed="""
def join_numbers(nums, sep=', '):
    return sep.join(str(n) for n in nums)
""".strip(),
    test="""
from solution import join_numbers

def test_basic():
    assert join_numbers([1, 2, 3]) == "1, 2, 3"

def test_empty():
    assert join_numbers([]) == ""

def test_single():
    assert join_numbers([42]) == "42"

def test_custom_sep():
    assert join_numbers([1, 2, 3], "-") == "1-2-3"
""".strip(),
)

T(
    "task_062", "type_error", "easy", 1,
    "integer_average uses integer division (//) instead of float division, truncating result",
    buggy="""
def average(nums):
    return sum(nums) // len(nums)
""".strip(),
    fixed="""
def average(nums):
    return sum(nums) / len(nums)
""".strip(),
    test="""
from solution import average

def test_exact():
    assert average([1, 2, 3]) == 2.0

def test_fractional():
    assert average([1, 2]) == 1.5

def test_negatives():
    assert average([-1, 1]) == 0.0
""".strip(),
)

T(
    "task_063", "type_error", "medium", 1,
    "compare_number_strings compares string lexicographically instead of numerically",
    buggy="""
def max_number_string(nums):
    return max(nums)
""".strip(),
    fixed="""
def max_number_string(nums):
    return max(nums, key=int)
""".strip(),
    test="""
from solution import max_number_string

def test_basic():
    assert max_number_string(["10", "9", "100"]) == "100"

def test_single():
    assert max_number_string(["5"]) == "5"

def test_same_digits():
    assert max_number_string(["21", "22", "20"]) == "22"
""".strip(),
)

T(
    "task_064", "type_error", "easy", 2,
    "sum_with_initial passes wrong type to sum(): sum(list, list) instead of sum(list, int)",
    buggy="""
def sum_with_initial(nums, initial):
    return sum(nums, [initial])
""".strip(),
    fixed="""
def sum_with_initial(nums, initial):
    return sum(nums, initial)
""".strip(),
    test="""
from solution import sum_with_initial

def test_zero():
    assert sum_with_initial([1, 2, 3], 0) == 6

def test_initial():
    assert sum_with_initial([1, 2, 3], 10) == 16

def test_empty():
    assert sum_with_initial([], 5) == 5
""".strip(),
)

T(
    "task_065", "type_error", "easy", 1,
    "number_to_string uses int() instead of str() when converting number",
    buggy="""
def number_to_string(n):
    return int(n)
""".strip(),
    fixed="""
def number_to_string(n):
    return str(n)
""".strip(),
    test="""
from solution import number_to_string

def test_int():
    assert number_to_string(42) == "42"

def test_zero():
    assert number_to_string(0) == "0"

def test_negative():
    assert number_to_string(-5) == "-5"

def test_type():
    assert isinstance(number_to_string(1), str)
""".strip(),
)

T(
    "task_066", "type_error", "medium", 1,
    "list_to_string uses str(list) instead of joining the list elements",
    buggy="""
def list_to_string(lst):
    return str(lst)
""".strip(),
    fixed="""
def list_to_string(lst):
    return ''.join(str(x) for x in lst)
""".strip(),
    test="""
from solution import list_to_string

def test_basic():
    assert list_to_string(['a', 'b', 'c']) == "abc"

def test_numbers():
    assert list_to_string([1, 2, 3]) == "123"

def test_empty():
    assert list_to_string([]) == ""
""".strip(),
)

T(
    "task_067", "type_error", "easy", 1,
    "float_comparison uses == for float comparison, failing due to floating point precision",
    buggy="""
def is_close_to_zero(x, tolerance=1e-9):
    return x == 0.0
""".strip(),
    fixed="""
def is_close_to_zero(x, tolerance=1e-9):
    return abs(x) < tolerance
""".strip(),
    test="""
from solution import is_close_to_zero

def test_zero():
    assert is_close_to_zero(0.0) is True

def test_near_zero():
    assert is_close_to_zero(1e-10) is True

def test_not_zero():
    assert is_close_to_zero(0.1) is False

def test_neg_near_zero():
    assert is_close_to_zero(-1e-10) is True
""".strip(),
)

T(
    "task_068", "type_error", "easy", 1,
    "set_difference uses list comprehension with wrong operator instead of set subtraction",
    buggy="""
def set_difference(a, b):
    return list(set(a) and set(b))
""".strip(),
    fixed="""
def set_difference(a, b):
    return sorted(set(a) - set(b))
""".strip(),
    test="""
from solution import set_difference

def test_basic():
    assert set_difference([1, 2, 3, 4], [3, 4, 5]) == [1, 2]

def test_empty_result():
    assert set_difference([1, 2], [1, 2, 3]) == []

def test_no_overlap():
    assert set_difference([1, 2], [3, 4]) == [1, 2]
""".strip(),
)

T(
    "task_069", "type_error", "medium", 1,
    "dict_values_sum sums dictionary keys instead of values",
    buggy="""
def sum_values(d):
    return sum(d.keys())
""".strip(),
    fixed="""
def sum_values(d):
    return sum(d.values())
""".strip(),
    test="""
from solution import sum_values

def test_basic():
    assert sum_values({"a": 1, "b": 2, "c": 3}) == 6

def test_single():
    assert sum_values({"x": 10}) == 10

def test_zero():
    assert sum_values({"a": 0, "b": 0}) == 0
""".strip(),
)

T(
    "task_070", "type_error", "easy", 1,
    "shallow_copy_bug modifies original list when modifying the copy due to missing deepcopy",
    buggy="""
def copy_and_append(lst, item):
    copy = lst.copy()
    copy.append(item)
    return copy, lst
""".strip(),
    fixed="""
def copy_and_append(lst, item):
    copy = lst.copy()
    copy.append(item)
    return copy, lst
""".strip(),
    test="""
from solution import copy_and_append

def test_original_unchanged():
    original = [1, 2, 3]
    result, orig = copy_and_append(original, 4)
    assert result == [1, 2, 3, 4]
    assert orig == [1, 2, 3]

def test_copy_has_item():
    result, _ = copy_and_append([1, 2], 99)
    assert 99 in result
""".strip(),
)

# task_070 correct in both. Replace.
TASKS.pop()

T(
    "task_070", "type_error", "easy", 1,
    "type_check uses type() == instead of isinstance(), failing for subclasses",
    buggy="""
def is_integer(x):
    return type(x) == int
""".strip(),
    fixed="""
def is_integer(x):
    return isinstance(x, int)
""".strip(),
    test="""
from solution import is_integer

def test_int():
    assert is_integer(5) is True

def test_float():
    assert is_integer(5.0) is False

def test_bool():
    # bool is a subclass of int; isinstance catches this
    assert is_integer(True) is True

def test_string():
    assert is_integer("5") is False
""".strip(),
)

# ===========================================================================
# API MISUSE (10 tasks)
# ===========================================================================

T(
    "task_071", "api_misuse", "easy", 1,
    "sort_in_place discards return value of list.sort(), returning None",
    buggy="""
def sorted_copy(lst):
    return lst.sort()
""".strip(),
    fixed="""
def sorted_copy(lst):
    return sorted(lst)
""".strip(),
    test="""
from solution import sorted_copy

def test_basic():
    result = sorted_copy([3, 1, 2])
    assert result == [1, 2, 3]

def test_unchanged_original():
    original = [3, 1, 2]
    result = sorted_copy(original)
    assert result is not None
    assert original == [3, 1, 2]

def test_empty():
    assert sorted_copy([]) == []
""".strip(),
)

T(
    "task_072", "api_misuse", "easy", 1,
    "append_list uses append(list) adding list as single element instead of extend(list)",
    buggy="""
def combine_lists(a, b):
    result = list(a)
    result.append(b)
    return result
""".strip(),
    fixed="""
def combine_lists(a, b):
    result = list(a)
    result.extend(b)
    return result
""".strip(),
    test="""
from solution import combine_lists

def test_basic():
    assert combine_lists([1, 2], [3, 4]) == [1, 2, 3, 4]

def test_empty_b():
    assert combine_lists([1, 2], []) == [1, 2]

def test_empty_a():
    assert combine_lists([], [1, 2]) == [1, 2]
""".strip(),
)

T(
    "task_073", "api_misuse", "easy", 1,
    "zip_unequal drops elements from longer list by using zip instead of zip_longest",
    buggy="""
def zip_fill(a, b, fill=None):
    return list(zip(a, b))
""".strip(),
    fixed="""
from itertools import zip_longest

def zip_fill(a, b, fill=None):
    return list(zip_longest(a, b, fillvalue=fill))
""".strip(),
    test="""
from solution import zip_fill

def test_equal():
    assert zip_fill([1, 2], ['a', 'b']) == [(1, 'a'), (2, 'b')]

def test_longer_a():
    assert zip_fill([1, 2, 3], ['a', 'b']) == [(1, 'a'), (2, 'b'), (3, None)]

def test_longer_b():
    assert zip_fill([1], ['a', 'b', 'c']) == [(1, 'a'), (None, 'b'), (None, 'c')]
""".strip(),
)

T(
    "task_074", "api_misuse", "easy", 1,
    "dict_setdefault uses assignment instead of setdefault, overwriting existing keys",
    buggy="""
def group_by_length(words):
    groups = {}
    for word in words:
        key = len(word)
        groups[key] = [word]
    return groups
""".strip(),
    fixed="""
def group_by_length(words):
    groups = {}
    for word in words:
        key = len(word)
        groups.setdefault(key, []).append(word)
    return groups
""".strip(),
    test="""
from solution import group_by_length

def test_basic():
    result = group_by_length(["hi", "bye", "go", "no"])
    assert sorted(result[2]) == ["go", "hi", "no"]
    assert result[3] == ["bye"]

def test_single():
    assert group_by_length(["hello"]) == {5: ["hello"]}

def test_empty():
    assert group_by_length([]) == {}
""".strip(),
)

T(
    "task_075", "api_misuse", "easy", 1,
    "string_strip strips wrong chars: strips 'ing' chars individually instead of the suffix",
    buggy="""
def remove_suffix_ing(word):
    return word.strip('ing')
""".strip(),
    fixed="""
def remove_suffix_ing(word):
    if word.endswith('ing'):
        return word[:-3]
    return word
""".strip(),
    test="""
from solution import remove_suffix_ing

def test_basic():
    assert remove_suffix_ing("running") == "runn"

def test_no_suffix():
    assert remove_suffix_ing("hello") == "hello"

def test_just_ing():
    assert remove_suffix_ing("ing") == ""

def test_singing():
    assert remove_suffix_ing("singing") == "sing"
""".strip(),
)

T(
    "task_076", "api_misuse", "easy", 1,
    "set_add_list uses set.add(list) raising TypeError instead of set.update(list)",
    buggy="""
def add_elements_to_set(s, elements):
    s = set(s)
    s.add(elements)
    return s
""".strip(),
    fixed="""
def add_elements_to_set(s, elements):
    s = set(s)
    s.update(elements)
    return s
""".strip(),
    test="""
from solution import add_elements_to_set

def test_basic():
    result = add_elements_to_set({1, 2}, [3, 4])
    assert result == {1, 2, 3, 4}

def test_duplicates():
    result = add_elements_to_set({1, 2}, [2, 3])
    assert result == {1, 2, 3}

def test_empty():
    result = add_elements_to_set(set(), [1, 2])
    assert result == {1, 2}
""".strip(),
)

T(
    "task_077", "api_misuse", "medium", 1,
    "map_applied discards map object, not converting to list",
    buggy="""
def double_all(nums):
    return map(lambda x: x * 2, nums)
""".strip(),
    fixed="""
def double_all(nums):
    return list(map(lambda x: x * 2, nums))
""".strip(),
    test="""
from solution import double_all

def test_basic():
    result = double_all([1, 2, 3])
    assert result == [2, 4, 6]

def test_empty():
    assert double_all([]) == []

def test_type():
    assert isinstance(double_all([1]), list)
""".strip(),
)

T(
    "task_078", "api_misuse", "easy", 1,
    "enumerate_wrong_start starts enumeration at 0 instead of 1 for 1-indexed positions",
    buggy="""
def rank_items(items):
    return [(i, item) for i, item in enumerate(items)]
""".strip(),
    fixed="""
def rank_items(items):
    return [(i, item) for i, item in enumerate(items, 1)]
""".strip(),
    test="""
from solution import rank_items

def test_basic():
    assert rank_items(['a', 'b', 'c']) == [(1, 'a'), (2, 'b'), (3, 'c')]

def test_single():
    assert rank_items(['x']) == [(1, 'x')]

def test_empty():
    assert rank_items([]) == []
""".strip(),
)

T(
    "task_079", "api_misuse", "easy", 1,
    "max_with_wrong_key finds max by string length instead of numeric value",
    buggy="""
def find_longest(words):
    return max(words, key=int)
""".strip(),
    fixed="""
def find_longest(words):
    return max(words, key=len)
""".strip(),
    test="""
from solution import find_longest

def test_basic():
    assert find_longest(["hi", "hello", "hey"]) == "hello"

def test_single():
    assert find_longest(["word"]) == "word"

def test_tie():
    result = find_longest(["ab", "cd"])
    assert len(result) == 2
""".strip(),
)

T(
    "task_080", "api_misuse", "easy", 1,
    "filter_kept keeps matching elements correctly but returns filter object, not list",
    buggy="""
def filter_positive(nums):
    return filter(lambda x: x > 0, nums)
""".strip(),
    fixed="""
def filter_positive(nums):
    return list(filter(lambda x: x > 0, nums))
""".strip(),
    test="""
from solution import filter_positive

def test_basic():
    assert filter_positive([1, -2, 3, -4]) == [1, 3]

def test_all_negative():
    assert filter_positive([-1, -2]) == []

def test_type():
    assert isinstance(filter_positive([1, 2]), list)
""".strip(),
)

# ===========================================================================
# BOUNDARY (10 tasks)
# ===========================================================================

T(
    "task_081", "boundary", "easy", 2,
    "single_element_max returns float('-inf') for single-element list due to loop not executing",
    buggy="""
def find_max_loop(nums):
    max_val = float('-inf')
    for i in range(1, len(nums)):
        if nums[i] > max_val:
            max_val = nums[i]
    return max_val
""".strip(),
    fixed="""
def find_max_loop(nums):
    max_val = nums[0]
    for i in range(1, len(nums)):
        if nums[i] > max_val:
            max_val = nums[i]
    return max_val
""".strip(),
    test="""
from solution import find_max_loop

def test_single():
    assert find_max_loop([42]) == 42

def test_multiple():
    assert find_max_loop([3, 1, 4, 1, 5]) == 5

def test_negatives():
    assert find_max_loop([-5, -1, -3]) == -1
""".strip(),
)

T(
    "task_082", "boundary", "easy", 2,
    "zero_power returns 0 for any base raised to power 0 due to wrong base case",
    buggy="""
def power(base, exp):
    if exp == 0:
        return 0
    return base * power(base, exp - 1)
""".strip(),
    fixed="""
def power(base, exp):
    if exp == 0:
        return 1
    return base * power(base, exp - 1)
""".strip(),
    test="""
from solution import power

def test_zero_exp():
    assert power(5, 0) == 1

def test_one_exp():
    assert power(5, 1) == 5

def test_two_exp():
    assert power(3, 2) == 9

def test_zero_base():
    assert power(0, 3) == 0
""".strip(),
)

T(
    "task_083", "boundary", "easy", 2,
    "negative_index: using -1 as sentinel causes collision with valid list index -1",
    buggy="""
def linear_search(lst, target):
    for i in range(len(lst)):
        if lst[i] == target:
            return i
    return -1
""".strip(),
    fixed="""
def linear_search(lst, target):
    for i in range(len(lst)):
        if lst[i] == target:
            return i
    return None
""".strip(),
    test="""
from solution import linear_search

def test_found():
    assert linear_search([1, 2, 3], 2) == 1

def test_not_found():
    assert linear_search([1, 2, 3], 5) is None

def test_first():
    assert linear_search([5, 3, 1], 5) == 0
""".strip(),
)

# task_083: both are "valid" depending on convention. Let me make a clearer boundary bug.
TASKS.pop()

T(
    "task_083", "boundary", "easy", 1,
    "fibonacci_zero returns 1 for n=0 instead of 0",
    buggy="""
def fib(n):
    if n <= 1:
        return 1
    return fib(n - 1) + fib(n - 2)
""".strip(),
    fixed="""
def fib(n):
    if n == 0:
        return 0
    if n == 1:
        return 1
    return fib(n - 1) + fib(n - 2)
""".strip(),
    test="""
from solution import fib

def test_zero():
    assert fib(0) == 0

def test_one():
    assert fib(1) == 1

def test_two():
    assert fib(2) == 1

def test_five():
    assert fib(5) == 5
""".strip(),
)

T(
    "task_084", "boundary", "easy", 2,
    "single_char_palindrome returns False for single-character string",
    buggy="""
def is_palindrome(s):
    if len(s) < 2:
        return False
    return s == s[::-1]
""".strip(),
    fixed="""
def is_palindrome(s):
    return s == s[::-1]
""".strip(),
    test="""
from solution import is_palindrome

def test_single_char():
    assert is_palindrome("a") is True

def test_palindrome():
    assert is_palindrome("racecar") is True

def test_not_palindrome():
    assert is_palindrome("hello") is False

def test_empty():
    assert is_palindrome("") is True
""".strip(),
)

T(
    "task_085", "boundary", "medium", 2,
    "median_single_element crashes or returns wrong value for single-element list",
    buggy="""
def median(nums):
    sorted_nums = sorted(nums)
    n = len(sorted_nums)
    mid = n // 2
    if n % 2 == 0:
        return (sorted_nums[mid - 1] + sorted_nums[mid]) / 2
    else:
        return sorted_nums[mid]
""".strip(),
    fixed="""
def median(nums):
    sorted_nums = sorted(nums)
    n = len(sorted_nums)
    mid = n // 2
    if n % 2 == 0:
        return (sorted_nums[mid - 1] + sorted_nums[mid]) / 2
    else:
        return sorted_nums[mid]
""".strip(),
    test="""
from solution import median

def test_odd():
    assert median([3, 1, 2]) == 2

def test_even():
    assert median([1, 2, 3, 4]) == 2.5

def test_single():
    assert median([7]) == 7

def test_all_same():
    assert median([5, 5, 5]) == 5
""".strip(),
)

# Both are correct. Replace.
TASKS.pop()

T(
    "task_085", "boundary", "easy", 2,
    "empty_string_split returns [''] instead of [] for empty string",
    buggy="""
def get_words(sentence):
    return sentence.split(' ')
""".strip(),
    fixed="""
def get_words(sentence):
    return sentence.split()
""".strip(),
    test="""
from solution import get_words

def test_basic():
    assert get_words("hello world") == ["hello", "world"]

def test_empty():
    assert get_words("") == []

def test_extra_spaces():
    assert get_words("hello  world") == ["hello", "world"]
""".strip(),
)

T(
    "task_086", "boundary", "easy", 2,
    "matrix_1x1_trace returns empty list instead of [element] for 1x1 matrix",
    buggy="""
def get_diagonal(matrix):
    n = len(matrix)
    return [matrix[i][i] for i in range(1, n)]
""".strip(),
    fixed="""
def get_diagonal(matrix):
    n = len(matrix)
    return [matrix[i][i] for i in range(n)]
""".strip(),
    test="""
from solution import get_diagonal

def test_3x3():
    assert get_diagonal([[1,2,3],[4,5,6],[7,8,9]]) == [1, 5, 9]

def test_2x2():
    assert get_diagonal([[1,2],[3,4]]) == [1, 4]

def test_1x1():
    assert get_diagonal([[7]]) == [7]
""".strip(),
)

T(
    "task_087", "boundary", "medium", 2,
    "already_sorted_quicksort picks first element as pivot causing O(n^2) and wrong boundary handling",
    buggy="""
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[0]
    left = [x for x in arr[1:] if x < pivot]
    right = [x for x in arr[1:] if x > pivot]
    return quicksort(left) + [pivot] + quicksort(right)
""".strip(),
    fixed="""
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)
""".strip(),
    test="""
from solution import quicksort

def test_basic():
    assert quicksort([3, 6, 8, 10, 1, 2, 1]) == [1, 1, 2, 3, 6, 8, 10]

def test_duplicates():
    assert quicksort([3, 3, 3]) == [3, 3, 3]

def test_empty():
    assert quicksort([]) == []

def test_single():
    assert quicksort([1]) == [1]

def test_sorted():
    assert quicksort([1, 2, 3, 4, 5]) == [1, 2, 3, 4, 5]
""".strip(),
)

T(
    "task_088", "boundary", "easy", 2,
    "power_of_two returns False for n=1 because it checks n>1 before the loop",
    buggy="""
def is_power_of_two(n):
    if n <= 0:
        return False
    while n > 1:
        if n % 2 != 0:
            return False
        n //= 2
    return True
""".strip(),
    fixed="""
def is_power_of_two(n):
    if n <= 0:
        return False
    while n > 1:
        if n % 2 != 0:
            return False
        n //= 2
    return True
""".strip(),
    test="""
from solution import is_power_of_two

def test_one():
    assert is_power_of_two(1) is True

def test_two():
    assert is_power_of_two(2) is True

def test_eight():
    assert is_power_of_two(8) is True

def test_not():
    assert is_power_of_two(6) is False

def test_zero():
    assert is_power_of_two(0) is False
""".strip(),
)

# This one is correct. Replace with a real boundary bug.
TASKS.pop()

T(
    "task_088", "boundary", "easy", 2,
    "absolute_value returns negative for INT_MIN-like case due to missing check",
    buggy="""
def absolute_value(n):
    if n < 0:
        return -n
    return n
""".strip(),
    fixed="""
def absolute_value(n):
    if n < 0:
        return -n
    return n
""".strip(),
    test="""
from solution import absolute_value

def test_positive():
    assert absolute_value(5) == 5

def test_negative():
    assert absolute_value(-3) == 3

def test_zero():
    assert absolute_value(0) == 0
""".strip(),
)

# Also correct. This is hard. Let me add actual real boundary bugs.
TASKS.pop()

T(
    "task_088", "boundary", "easy", 2,
    "clamp returns wrong value at exact boundary due to strict < instead of <=",
    buggy="""
def clamp(value, min_val, max_val):
    if value < min_val:
        return min_val
    if value > max_val:
        return max_val
    return value
""".strip(),
    fixed="""
def clamp(value, min_val, max_val):
    if value < min_val:
        return min_val
    if value > max_val:
        return max_val
    return value
""".strip(),
    test="""
from solution import clamp

def test_below():
    assert clamp(0, 1, 10) == 1

def test_above():
    assert clamp(15, 1, 10) == 10

def test_in_range():
    assert clamp(5, 1, 10) == 5

def test_at_min():
    assert clamp(1, 1, 10) == 1

def test_at_max():
    assert clamp(10, 1, 10) == 10
""".strip(),
)

# Still correct. Let me think differently for task_088-090.
TASKS.pop()

T(
    "task_088", "boundary", "easy", 1,
    "modulo_by_zero returns 0 instead of raising when divisor is 0 in safe_mod",
    buggy="""
def safe_mod(a, b):
    if b == 0:
        return 0
    return a % b
""".strip(),
    fixed="""
def safe_mod(a, b):
    if b == 0:
        return None
    return a % b
""".strip(),
    test="""
from solution import safe_mod

def test_normal():
    assert safe_mod(10, 3) == 1

def test_zero_divisor():
    assert safe_mod(5, 0) is None

def test_exact():
    assert safe_mod(6, 3) == 0
""".strip(),
)

T(
    "task_089", "boundary", "easy", 1,
    "string_repeat returns empty string for n=0 instead of empty string (wrong initial value)",
    buggy="""
def repeat_string(s, n):
    result = s
    for _ in range(n - 1):
        result += s
    return result
""".strip(),
    fixed="""
def repeat_string(s, n):
    result = ''
    for _ in range(n):
        result += s
    return result
""".strip(),
    test="""
from solution import repeat_string

def test_basic():
    assert repeat_string("ab", 3) == "ababab"

def test_once():
    assert repeat_string("hello", 1) == "hello"

def test_zero():
    assert repeat_string("hi", 0) == ""

def test_empty_string():
    assert repeat_string("", 5) == ""
""".strip(),
)

T(
    "task_090", "boundary", "medium", 2,
    "all_same_elements causes wrong result for list where all elements are equal",
    buggy="""
def has_duplicates(lst):
    return len(lst) != len(set(lst))
""".strip(),
    fixed="""
def has_duplicates(lst):
    return len(lst) != len(set(lst))
""".strip(),
    test="""
from solution import has_duplicates

def test_with_dup():
    assert has_duplicates([1, 2, 2, 3]) is True

def test_no_dup():
    assert has_duplicates([1, 2, 3]) is False

def test_all_same():
    assert has_duplicates([5, 5, 5]) is True

def test_empty():
    assert has_duplicates([]) is False

def test_single():
    assert has_duplicates([1]) is False
""".strip(),
)

# task_090 correct. Replace.
TASKS.pop()

T(
    "task_090", "boundary", "easy", 1,
    "string_title uses wrong method: upper() instead of title() capitalizing everything",
    buggy="""
def title_case(s):
    return s.upper()
""".strip(),
    fixed="""
def title_case(s):
    return s.title()
""".strip(),
    test="""
from solution import title_case

def test_basic():
    assert title_case("hello world") == "Hello World"

def test_already():
    assert title_case("Python Is Fun") == "Python Is Fun"

def test_all_lower():
    assert title_case("foo bar") == "Foo Bar"

def test_empty():
    assert title_case("") == ""
""".strip(),
)

# ===========================================================================
# Build and validate
# ===========================================================================

def build_benchmark(output_dir: Path, validate: bool = False) -> None:
    tasks_dir = output_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)

    print(f"Building {len(TASKS)} tasks in {tasks_dir}")
    failed_validation = []

    for task in TASKS:
        tid = task["task_id"]
        task_dir = tasks_dir / tid
        task_dir.mkdir(exist_ok=True)

        (task_dir / "buggy.py").write_text(task["buggy"].strip() + "\n", encoding="utf-8")
        (task_dir / "fixed.py").write_text(task["fixed"].strip() + "\n", encoding="utf-8")
        (task_dir / "test_suite.py").write_text(task["test"].strip() + "\n", encoding="utf-8")

        meta = {
            "task_id": tid,
            "source": task["source"],
            "category": task["category"],
            "difficulty": task["difficulty"],
            "lines_changed": task["lines_changed"],
            "description": task["description"],
        }
        (task_dir / "metadata.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )

        if validate:
            ok, msg = validate_task(task_dir)
            status = "OK" if ok else "FAIL"
            print(f"  [{status}] {tid}: {msg}")
            if not ok:
                failed_validation.append((tid, msg))

    print(f"\nGenerated {len(TASKS)} tasks.")
    if validate:
        if failed_validation:
            print(f"\n{len(failed_validation)} tasks failed validation:")
            for tid, msg in failed_validation:
                print(f"  {tid}: {msg}")
        else:
            print("All tasks validated successfully.")
    return failed_validation


def validate_task(task_dir: Path) -> tuple[bool, str]:
    """Returns (is_valid, message). Valid means buggy fails tests and fixed passes tests."""
    buggy = (task_dir / "buggy.py").read_text(encoding="utf-8")
    fixed = (task_dir / "fixed.py").read_text(encoding="utf-8")

    buggy_passes = _run_tests(task_dir, buggy)   # True = tests PASS with buggy code
    if buggy_passes is None:
        return False, "timeout on buggy"
    fixed_passes = _run_tests(task_dir, fixed)   # True = tests PASS with fixed code
    if fixed_passes is None:
        return False, "timeout on fixed"

    if not buggy_passes and fixed_passes:
        return True, "buggy fails, fixed passes"
    elif buggy_passes and fixed_passes:
        return False, "WARNING: buggy also passes (bug not detectable by tests)"
    elif not buggy_passes and not fixed_passes:
        return False, "ERROR: fixed does not pass tests"
    else:
        return False, "ERROR: both fail"


def _run_tests(task_dir: Path, solution_code: str) -> bool | None:
    """Returns True if tests pass, False if they fail, None on timeout."""
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        shutil.copy(task_dir / "test_suite.py", tmpdir / "test_suite.py")
        (tmpdir / "solution.py").write_text(solution_code, encoding="utf-8")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "test_suite.py", "-q", "--tb=no", "--no-header"],
                cwd=tmpdir,
                capture_output=True,
                timeout=15,
                text=True,
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return None


def validate_only(output_dir: Path) -> list:
    """Validate existing task directories without rebuilding."""
    tasks_dir = output_dir / "tasks"
    failed = []
    task_dirs = sorted(tasks_dir.glob("task_*"))
    print(f"Validating {len(task_dirs)} existing tasks in {tasks_dir}")
    for task_dir in task_dirs:
        if not task_dir.is_dir():
            continue
        tid = task_dir.name
        ok, msg = validate_task(task_dir)
        status = "OK" if ok else "FAIL"
        print(f"  [{status}] {tid}: {msg}")
        if not ok:
            failed.append((tid, msg))
    print(f"\nValidated {len(task_dirs)} tasks.")
    if failed:
        print(f"\n{len(failed)} tasks failed:")
        for tid, msg in failed:
            print(f"  {tid}: {msg}")
    else:
        print("All tasks validated successfully.")
    return failed


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true", help="Build then validate all tasks")
    parser.add_argument("--validate-only", action="store_true", help="Validate existing tasks without rebuilding")
    parser.add_argument("--output", default=str(Path(__file__).parent), help="Output directory")
    args = parser.parse_args()

    output_dir = Path(args.output)
    if args.validate_only:
        validate_only(output_dir)
    else:
        build_benchmark(output_dir, validate=args.validate)
