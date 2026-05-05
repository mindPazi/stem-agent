"""Build and validate the self-contained Stem Agent bug-repair benchmark.

This file is the canonical source for the Day 1 benchmark. It generates the
same 90 validated tasks that are used locally under benchmark/tasks/.
Each task contains buggy.py, fixed.py, test_suite.py, and metadata.json.

Usage:
    python benchmark/build_benchmark.py
    python benchmark/build_benchmark.py --validate
    python benchmark/build_benchmark.py --validate-only
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

TaskDef = dict[str, Any]

TASKS: list[TaskDef] = [
    {
        'task_id': 'task_001',
        'source': 'mutation_exercism',
        'category': 'off_by_one',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'binary_search uses high=len(arr) causing IndexError when target exceeds all elements',
        'buggy': 'def binary_search(arr, target):\n    low, high = 0, len(arr)\n    while low <= high:\n        mid = (low + high) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            low = mid + 1\n        else:\n            high = mid - 1\n    return -1\n',
        'fixed': 'def binary_search(arr, target):\n    low, high = 0, len(arr) - 1\n    while low <= high:\n        mid = (low + high) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            low = mid + 1\n        else:\n            high = mid - 1\n    return -1\n',
        'test': 'import random\nfrom solution import binary_search\n\n\ndef _check(arr, target):\n    res = binary_search(arr, target)\n    if target in arr:\n        assert res != -1 and arr[res] == target\n    else:\n        assert res == -1\n\n\ndef test_random_sorted():\n    random.seed(0)\n    for _ in range(20):\n        arr = sorted(random.sample(range(-50, 50), random.randint(1, 20)))\n        target = random.choice(arr + [99, -99])\n        _check(arr, target)\n\n\ndef test_target_above_all():\n    _check([1, 3, 5, 7, 9], 100)\n\n\ndef test_target_below_all():\n    _check([1, 3, 5, 7, 9], -100)\n\n\ndef test_single_element():\n    _check([42], 42)\n    _check([42], 0)\n\n',
    },
    {
        'task_id': 'task_002',
        'source': 'mutation_exercism',
        'category': 'off_by_one',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'Fibonacci returns fib(n-1) instead of fib(n) due to off-by-one in loop range',
        'buggy': 'def fibonacci(n):\n    if n <= 0:\n        return 0\n    a, b = 0, 1\n    for _ in range(n - 1):\n        a, b = b, a + b\n    return a\n',
        'fixed': 'def fibonacci(n):\n    if n <= 0:\n        return 0\n    a, b = 0, 1\n    for _ in range(n - 1):\n        a, b = b, a + b\n    return b\n',
        'test': 'from solution import fibonacci\n\n\ndef _ref(n):\n    if n <= 0:\n        return 0\n    a, b = 0, 1\n    for _ in range(n - 1):\n        a, b = b, a + b\n    return b\n\n\ndef test_matches_reference():\n    for n in [0, 1, 2, 3, 5, 7, 10, 15, 20]:\n        assert fibonacci(n) == _ref(n)\n\n\ndef test_recurrence():\n    for n in range(2, 15):\n        assert fibonacci(n) == fibonacci(n - 1) + fibonacci(n - 2)\n\n',
    },
    {
        'task_id': 'task_003',
        'source': 'mutation_exercism',
        'category': 'off_by_one',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'rotate_list slices at k+1 instead of k, shifting one extra element',
        'buggy': 'def rotate_list(lst, k):\n    if not lst:\n        return lst\n    k = k % len(lst)\n    return lst[k + 1:] + lst[:k + 1]\n',
        'fixed': 'def rotate_list(lst, k):\n    if not lst:\n        return lst\n    k = k % len(lst)\n    return lst[k:] + lst[:k]\n',
        'test': 'from solution import rotate_list\n\n\ndef test_rotation_preserves_elements():\n    for k in range(0, 8):\n        out = rotate_list([1, 2, 3, 4, 5], k)\n        assert sorted(out) == [1, 2, 3, 4, 5]\n\n\ndef test_rotation_amount():\n    arr = [10, 20, 30, 40, 50]\n    for k in range(0, 12):\n        out = rotate_list(list(arr), k)\n        assert out == arr[k % len(arr):] + arr[:k % len(arr)]\n\n\ndef test_empty_list():\n    assert rotate_list([], 3) == []\n\n',
    },
    {
        'task_id': 'task_004',
        'source': 'mutation_exercism',
        'category': 'off_by_one',
        'difficulty': 'medium',
        'lines_changed': 1,
        'description': 'count_substrings uses range(n - len(sub)) missing the last valid start position',
        'buggy': 'def count_substrings(s, sub):\n    count = 0\n    for i in range(len(s) - len(sub)):\n        if s[i:i + len(sub)] == sub:\n            count += 1\n    return count\n',
        'fixed': 'def count_substrings(s, sub):\n    count = 0\n    for i in range(len(s) - len(sub) + 1):\n        if s[i:i + len(sub)] == sub:\n            count += 1\n    return count\n',
        'test': 'import random\nfrom solution import count_substrings\n\n\ndef _ref(s, sub):\n    return sum(1 for i in range(len(s) - len(sub) + 1) if s[i:i + len(sub)] == sub)\n\n\ndef test_matches_reference():\n    cases = [\n        ("abc", "abc"), ("hello", "l"), ("hello", "z"),\n        ("abab", "ab"), ("aaaa", "aa"), ("xyz", "a"),\n    ]\n    for s, sub in cases:\n        assert count_substrings(s, sub) == _ref(s, sub)\n\n\ndef test_random_inputs():\n    random.seed(1)\n    for _ in range(20):\n        s = "".join(random.choice("ab") for _ in range(random.randint(2, 12)))\n        sub = "".join(random.choice("ab") for _ in range(random.randint(1, 3)))\n        assert count_substrings(s, sub) == _ref(s, sub)\n\n',
    },
    {
        'task_id': 'task_005',
        'source': 'mutation_exercism',
        'category': 'off_by_one',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'remove_duplicates appends when arr[i] == arr[i+1] (inverted condition)',
        'buggy': 'def remove_duplicates(arr):\n    if not arr:\n        return []\n    result = []\n    for i in range(len(arr) - 1):\n        if arr[i] == arr[i + 1]:\n            result.append(arr[i])\n    result.append(arr[-1])\n    return result\n',
        'fixed': 'def remove_duplicates(arr):\n    if not arr:\n        return []\n    result = []\n    for i in range(len(arr) - 1):\n        if arr[i] != arr[i + 1]:\n            result.append(arr[i])\n    result.append(arr[-1])\n    return result\n',
        'test': 'from solution import remove_duplicates\n\n\ndef test_consecutive_duplicates_collapsed():\n    cases = [\n        [1, 1, 2, 3, 3, 4],\n        [1, 2, 3, 4],\n        [5, 5, 5, 5],\n        [1],\n        [],\n        [1, 1, 1, 2, 1, 1],\n    ]\n    for arr in cases:\n        out = remove_duplicates(list(arr))\n        # property: no two consecutive equal in output\n        assert all(out[i] != out[i + 1] for i in range(len(out) - 1))\n        # property: collapsing arr by adjacent-equality must equal out\n        ref = []\n        for x in arr:\n            if not ref or ref[-1] != x:\n                ref.append(x)\n        assert out == ref\n\n',
    },
    {
        'task_id': 'task_006',
        'source': 'mutation_exercism',
        'category': 'off_by_one',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'two_sum_indices returns 0-indexed but problem expects 1-indexed results',
        'buggy': 'def two_sum(nums, target):\n    seen = {}\n    for i, num in enumerate(nums):\n        complement = target - num\n        if complement in seen:\n            return [seen[complement], i]\n        seen[num] = i\n    return []\n',
        'fixed': 'def two_sum(nums, target):\n    seen = {}\n    for i, num in enumerate(nums):\n        complement = target - num\n        if complement in seen:\n            return [seen[complement] + 1, i + 1]\n        seen[num] = i\n    return []\n',
        'test': 'from solution import two_sum\n\n\ndef _check(nums, target):\n    res = two_sum(nums, target)\n    if not res:\n        # no pair sums to target\n        assert all(nums[i] + nums[j] != target for i in range(len(nums)) for j in range(i + 1, len(nums)))\n    else:\n        i1, i2 = res\n        # 1-indexed per spec\n        assert 1 <= i1 < i2 <= len(nums)\n        assert nums[i1 - 1] + nums[i2 - 1] == target\n\n\ndef test_various():\n    _check([2, 7, 11, 15], 9)\n    _check([3, 2, 4], 6)\n    _check([3, 3], 6)\n    _check([1, 5, 9], 100)\n    _check([10, 20, 30, 40], 50)\n\n',
    },
    {
        'task_id': 'task_007',
        'source': 'mutation_exercism',
        'category': 'off_by_one',
        'difficulty': 'medium',
        'lines_changed': 1,
        'description': 'sliding_window_max uses window of size k+1 instead of k',
        'buggy': 'def max_sliding_window(nums, k):\n    result = []\n    for i in range(len(nums) - k + 1):\n        result.append(max(nums[i:i + k + 1]))\n    return result\n',
        'fixed': 'def max_sliding_window(nums, k):\n    result = []\n    for i in range(len(nums) - k + 1):\n        result.append(max(nums[i:i + k]))\n    return result\n',
        'test': 'from solution import max_sliding_window\n\n\ndef _ref(nums, k):\n    return [max(nums[i:i + k]) for i in range(len(nums) - k + 1)]\n\n\ndef test_matches_reference():\n    cases = [\n        ([1, 3, -1, -3, 5, 3, 6, 7], 3),\n        ([1, 2, 3, 4, 5], 1),\n        ([5, 4, 3, 2, 1], 2),\n        ([1, 1, 1, 1], 4),\n    ]\n    for nums, k in cases:\n        assert max_sliding_window(nums, k) == _ref(nums, k)\n\n',
    },
    {
        'task_id': 'task_008',
        'source': 'mutation_exercism',
        'category': 'off_by_one',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'count_pairs_with_sum checks arr[i]+arr[j] == target*2 instead of target',
        'buggy': 'def count_pairs_with_sum(arr, target):\n    count = 0\n    n = len(arr)\n    for i in range(n):\n        for j in range(i + 1, n):\n            if arr[i] + arr[j] == target * 2:\n                count += 1\n    return count\n',
        'fixed': 'def count_pairs_with_sum(arr, target):\n    count = 0\n    n = len(arr)\n    for i in range(n):\n        for j in range(i + 1, n):\n            if arr[i] + arr[j] == target:\n                count += 1\n    return count\n',
        'test': 'from solution import count_pairs_with_sum\n\n\ndef _ref(arr, target):\n    n = len(arr)\n    return sum(1 for i in range(n) for j in range(i + 1, n) if arr[i] + arr[j] == target)\n\n\ndef test_matches_reference():\n    cases = [\n        ([1, 2, 3, 4], 5),\n        ([1, 1, 1, 1], 2),\n        ([0, 0, 0], 0),\n        ([5], 5),\n        ([], 3),\n        ([-1, 1, 2, -2], 0),\n    ]\n    for arr, t in cases:\n        assert count_pairs_with_sum(arr, t) == _ref(arr, t)\n\n',
    },
    {
        'task_id': 'task_009',
        'source': 'mutation_exercism',
        'category': 'off_by_one',
        'difficulty': 'medium',
        'lines_changed': 1,
        'description': 'matrix_diagonal_sum iterates range(n+1) causing IndexError on last iteration',
        'buggy': 'def diagonal_sum(matrix):\n    n = len(matrix)\n    total = 0\n    for i in range(n + 1):\n        total += matrix[i][i]\n    return total\n',
        'fixed': 'def diagonal_sum(matrix):\n    n = len(matrix)\n    total = 0\n    for i in range(n):\n        total += matrix[i][i]\n    return total\n',
        'test': 'from solution import diagonal_sum\n\n\ndef _ref(m):\n    return sum(m[i][i] for i in range(len(m)))\n\n\ndef test_matches_reference():\n    cases = [\n        [[1, 2], [3, 4]],\n        [[1, 0, 0], [0, 2, 0], [0, 0, 3]],\n        [[5]],\n        [[1, 2, 3], [4, 5, 6], [7, 8, 9]],\n    ]\n    for m in cases:\n        assert diagonal_sum(m) == _ref(m)\n\n',
    },
    {
        'task_id': 'task_010',
        'source': 'mutation_exercism',
        'category': 'off_by_one',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'caesar_cipher shifts by n-1 instead of n due to subtraction in modulo',
        'buggy': "def caesar_cipher(text, shift):\n    result = []\n    for ch in text:\n        if ch.isalpha():\n            base = ord('A') if ch.isupper() else ord('a')\n            result.append(chr((ord(ch) - base + shift - 1) % 26 + base))\n        else:\n            result.append(ch)\n    return ''.join(result)\n",
        'fixed': "def caesar_cipher(text, shift):\n    result = []\n    for ch in text:\n        if ch.isalpha():\n            base = ord('A') if ch.isupper() else ord('a')\n            result.append(chr((ord(ch) - base + shift) % 26 + base))\n        else:\n            result.append(ch)\n    return ''.join(result)\n",
        'test': 'from solution import caesar_cipher\n\n\ndef test_round_trip():\n    for shift in [1, 3, 7, 13, 25]:\n        text = "Hello, World! 123"\n        enc = caesar_cipher(text, shift)\n        dec = caesar_cipher(enc, -shift)\n        assert dec == text\n\n\ndef test_alpha_only_shifts():\n    out = caesar_cipher("abc", 1)\n    assert out == "bcd"\n    out = caesar_cipher("XYZ", 3)\n    assert out == "ABC"\n    # non-alpha untouched\n    assert caesar_cipher("a-b!", 1) == "b-c!"\n\n\ndef test_zero_shift():\n    assert caesar_cipher("hello", 0) == "hello"\n\n',
    },
    {
        'task_id': 'task_011',
        'source': 'mutation_exercism',
        'category': 'off_by_one',
        'difficulty': 'medium',
        'lines_changed': 1,
        'description': 'run_length_encode initializes count to 2 instead of 1, inflating all counts by 1',
        'buggy': "def run_length_encode(s):\n    if not s:\n        return ''\n    result = []\n    count = 2\n    for i in range(1, len(s)):\n        if s[i] == s[i - 1]:\n            count += 1\n        else:\n            result.append(f'{count}{s[i-1]}')\n            count = 2\n    result.append(f'{count}{s[-1]}')\n    return ''.join(result)\n",
        'fixed': "def run_length_encode(s):\n    if not s:\n        return ''\n    result = []\n    count = 1\n    for i in range(1, len(s)):\n        if s[i] == s[i - 1]:\n            count += 1\n        else:\n            result.append(f'{count}{s[i-1]}')\n            count = 1\n    result.append(f'{count}{s[-1]}')\n    return ''.join(result)\n",
        'test': 'from solution import run_length_encode\n\n\ndef _decode(rle):\n    # parse "<count><char>" pairs\n    out = []\n    i = 0\n    while i < len(rle):\n        j = i\n        while j < len(rle) and rle[j].isdigit():\n            j += 1\n        n = int(rle[i:j])\n        ch = rle[j]\n        out.append(ch * n)\n        i = j + 1\n    return "".join(out)\n\n\ndef test_round_trip():\n    for s in ["aaabb", "abcd", "a", "", "wwwwbbbcdaa", "zzz"]:\n        enc = run_length_encode(s)\n        assert _decode(enc) == s\n\n',
    },
    {
        'task_id': 'task_012',
        'source': 'mutation_exercism',
        'category': 'off_by_one',
        'difficulty': 'medium',
        'lines_changed': 1,
        'description': 'next_greater_element uses >= instead of >, incorrectly returning equal elements',
        'buggy': 'def next_greater_element(arr):\n    n = len(arr)\n    result = [-1] * n\n    for i in range(n):\n        for j in range(i + 1, n):\n            if arr[j] >= arr[i]:\n                result[i] = arr[j]\n                break\n    return result\n',
        'fixed': 'def next_greater_element(arr):\n    n = len(arr)\n    result = [-1] * n\n    for i in range(n):\n        for j in range(i + 1, n):\n            if arr[j] > arr[i]:\n                result[i] = arr[j]\n                break\n    return result\n',
        'test': 'from solution import next_greater_element\n\n\ndef _ref(arr):\n    n = len(arr)\n    out = [-1] * n\n    for i in range(n):\n        for j in range(i + 1, n):\n            if arr[j] > arr[i]:\n                out[i] = arr[j]\n                break\n    return out\n\n\ndef test_matches_reference():\n    cases = [\n        [4, 5, 2, 25],\n        [13, 7, 6, 12],\n        [1, 2, 3, 4],\n        [4, 3, 2, 1],\n        [1, 1, 1],\n        [],\n    ]\n    for arr in cases:\n        assert next_greater_element(arr) == _ref(arr)\n\n',
    },
    {
        'task_id': 'task_013',
        'source': 'mutation_exercism',
        'category': 'off_by_one',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'string_reverse iterates to len(s)//2 + 1, overwriting the middle of odd strings',
        'buggy': "def reverse_string(s):\n    lst = list(s)\n    n = len(lst)\n    for i in range(n // 2 + 1):\n        lst[i], lst[n - 1 - i] = lst[n - 1 - i], lst[i]\n    return ''.join(lst)\n",
        'fixed': "def reverse_string(s):\n    lst = list(s)\n    n = len(lst)\n    for i in range(n // 2):\n        lst[i], lst[n - 1 - i] = lst[n - 1 - i], lst[i]\n    return ''.join(lst)\n",
        'test': 'from solution import reverse_string\n\n\ndef test_matches_reference():\n    for s in ["abc", "hello", "", "a", "ab", "racecar", "abcdef"]:\n        assert reverse_string(s) == s[::-1]\n\n',
    },
    {
        'task_id': 'task_014',
        'source': 'mutation_exercism',
        'category': 'off_by_one',
        'difficulty': 'medium',
        'lines_changed': 1,
        'description': 'majority_element uses wrong threshold: n//2 instead of n//2 + 1 allowing non-majority',
        'buggy': 'def majority_element(nums):\n    n = len(nums)\n    counts = {}\n    for num in nums:\n        counts[num] = counts.get(num, 0) + 1\n        if counts[num] >= n // 2:\n            return num\n    return -1\n',
        'fixed': 'def majority_element(nums):\n    n = len(nums)\n    counts = {}\n    for num in nums:\n        counts[num] = counts.get(num, 0) + 1\n        if counts[num] > n // 2:\n            return num\n    return -1\n',
        'test': 'from collections import Counter\nfrom solution import majority_element\n\n\ndef _ref(nums):\n    n = len(nums)\n    if n == 0:\n        return -1\n    c = Counter(nums)\n    candidate, count = c.most_common(1)[0]\n    return candidate if count > n // 2 else -1\n\n\ndef test_matches_reference():\n    cases = [\n        [3, 2, 3], [2, 2, 1, 1, 1, 2, 2], [1, 1, 2, 2],\n        [5, 5, 5], [1, 1], [1, 2], [1, 2, 3, 4],\n    ]\n    for nums in cases:\n        assert majority_element(nums) == _ref(nums)\n\n',
    },
    {
        'task_id': 'task_015',
        'source': 'mutation_exercism',
        'category': 'off_by_one',
        'difficulty': 'medium',
        'lines_changed': 1,
        'description': 'trap_rain_water uses max(left_max, right_max) instead of min, computing wrong water level',
        'buggy': 'def trap_rain_water(height):\n    n = len(height)\n    if n < 3:\n        return 0\n    left_max = [0] * n\n    right_max = [0] * n\n    left_max[0] = height[0]\n    for i in range(1, n):\n        left_max[i] = max(left_max[i - 1], height[i])\n    right_max[n - 1] = height[n - 1]\n    for i in range(n - 2, -1, -1):\n        right_max[i] = max(right_max[i + 1], height[i])\n    water = 0\n    for i in range(n):\n        water += max(left_max[i], right_max[i]) - height[i]\n    return water\n',
        'fixed': 'def trap_rain_water(height):\n    n = len(height)\n    if n < 3:\n        return 0\n    left_max = [0] * n\n    right_max = [0] * n\n    left_max[0] = height[0]\n    for i in range(1, n):\n        left_max[i] = max(left_max[i - 1], height[i])\n    right_max[n - 1] = height[n - 1]\n    for i in range(n - 2, -1, -1):\n        right_max[i] = max(right_max[i + 1], height[i])\n    water = 0\n    for i in range(n):\n        water += min(left_max[i], right_max[i]) - height[i]\n    return water\n',
        'test': 'from solution import trap_rain_water\n\n\ndef _ref(height):\n    n = len(height)\n    if n < 3:\n        return 0\n    left = [0] * n\n    right = [0] * n\n    left[0] = height[0]\n    for i in range(1, n):\n        left[i] = max(left[i - 1], height[i])\n    right[-1] = height[-1]\n    for i in range(n - 2, -1, -1):\n        right[i] = max(right[i + 1], height[i])\n    return sum(min(left[i], right[i]) - height[i] for i in range(n))\n\n\ndef test_matches_reference():\n    cases = [\n        [0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1],\n        [3, 0, 3],\n        [3, 2, 1],\n        [1, 2],\n        [],\n        [4, 2, 0, 3, 2, 5],\n    ]\n    for h in cases:\n        assert trap_rain_water(h) == _ref(h)\n\n',
    },
    {
        'task_id': 'task_016',
        'source': 'mutation_exercism',
        'category': 'wrong_variable',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'bubble_sort swaps arr[j] with arr[j] instead of arr[j+1]',
        'buggy': 'def bubble_sort(arr):\n    n = len(arr)\n    for i in range(n):\n        for j in range(0, n - i - 1):\n            if arr[j] > arr[j + 1]:\n                arr[j], arr[j] = arr[j + 1], arr[j]\n    return arr\n',
        'fixed': 'def bubble_sort(arr):\n    n = len(arr)\n    for i in range(n):\n        for j in range(0, n - i - 1):\n            if arr[j] > arr[j + 1]:\n                arr[j], arr[j + 1] = arr[j + 1], arr[j]\n    return arr\n',
        'test': 'import random\nfrom solution import bubble_sort\n\n\ndef test_sorts_correctly():\n    random.seed(2)\n    for _ in range(15):\n        arr = [random.randint(-20, 20) for _ in range(random.randint(0, 10))]\n        out = bubble_sort(list(arr))\n        assert out == sorted(arr)\n\n\ndef test_already_sorted():\n    assert bubble_sort([1, 2, 3, 4, 5]) == [1, 2, 3, 4, 5]\n\n\ndef test_reverse_sorted():\n    assert bubble_sort([5, 4, 3, 2, 1]) == [1, 2, 3, 4, 5]\n\n',
    },
    {
        'task_id': 'task_017',
        'source': 'mutation_exercism',
        'category': 'wrong_variable',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'gcd passes (a, b%a) instead of (b, a%b) causing infinite recursion or wrong result',
        'buggy': 'def gcd(a, b):\n    if b == 0:\n        return a\n    return gcd(a, b % a)\n',
        'fixed': 'def gcd(a, b):\n    if b == 0:\n        return a\n    return gcd(b, a % b)\n',
        'test': 'import math\nfrom solution import gcd\n\n\ndef test_matches_math_gcd():\n    pairs = [(48, 18), (100, 75), (17, 13), (1, 1), (12, 0), (0, 12), (270, 192)]\n    for a, b in pairs:\n        assert gcd(a, b) == math.gcd(a, b)\n\n',
    },
    {
        'task_id': 'task_018',
        'source': 'mutation_exercism',
        'category': 'wrong_variable',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'max_profit tracks max_price instead of min_price, never updates the buy signal correctly',
        'buggy': 'def max_profit(prices):\n    if not prices:\n        return 0\n    max_price = prices[0]\n    profit = 0\n    for price in prices[1:]:\n        profit = max(profit, price - max_price)\n        max_price = max(max_price, price)\n    return profit\n',
        'fixed': 'def max_profit(prices):\n    if not prices:\n        return 0\n    min_price = prices[0]\n    profit = 0\n    for price in prices[1:]:\n        profit = max(profit, price - min_price)\n        min_price = min(min_price, price)\n    return profit\n',
        'test': 'from solution import max_profit\n\n\ndef _ref(prices):\n    if not prices:\n        return 0\n    best = 0\n    lo = prices[0]\n    for p in prices[1:]:\n        best = max(best, p - lo)\n        lo = min(lo, p)\n    return best\n\n\ndef test_matches_reference():\n    cases = [\n        [7, 1, 5, 3, 6, 4],\n        [7, 6, 4, 3, 1],\n        [5],\n        [1, 5],\n        [],\n        [2, 4, 1, 7, 3, 9],\n    ]\n    for p in cases:\n        assert max_profit(p) == _ref(p)\n\n',
    },
    {
        'task_id': 'task_019',
        'source': 'mutation_exercism',
        'category': 'wrong_variable',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'string_compression appends char before count, producing reversed encoding',
        'buggy': "def compress_string(s):\n    if not s:\n        return ''\n    result = []\n    count = 1\n    for i in range(1, len(s)):\n        if s[i] == s[i - 1]:\n            count += 1\n        else:\n            result.append(s[i] + str(count))\n            count = 1\n    result.append(s[-1] + str(count))\n    return ''.join(result)\n",
        'fixed': "def compress_string(s):\n    if not s:\n        return ''\n    result = []\n    count = 1\n    for i in range(1, len(s)):\n        if s[i] == s[i - 1]:\n            count += 1\n        else:\n            result.append(s[i - 1] + str(count))\n            count = 1\n    result.append(s[-1] + str(count))\n    return ''.join(result)\n",
        'test': 'from solution import compress_string\n\n\ndef _ref(s):\n    if not s:\n        return ""\n    out = []\n    count = 1\n    for i in range(1, len(s)):\n        if s[i] == s[i - 1]:\n            count += 1\n        else:\n            out.append(s[i - 1] + str(count))\n            count = 1\n    out.append(s[-1] + str(count))\n    return "".join(out)\n\n\ndef test_matches_reference():\n    for s in ["aaabb", "abcd", "a", "", "aabbccdd", "wwwwbbbcd"]:\n        assert compress_string(s) == _ref(s)\n\n',
    },
    {
        'task_id': 'task_020',
        'source': 'mutation_exercism',
        'category': 'wrong_variable',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'find_second_largest returns largest instead of second largest',
        'buggy': "def find_second_largest(nums):\n    first = second = float('-inf')\n    for num in nums:\n        if num > first:\n            second = first\n            first = num\n        elif num > second and num != first:\n            second = num\n    return first\n",
        'fixed': "def find_second_largest(nums):\n    first = second = float('-inf')\n    for num in nums:\n        if num > first:\n            second = first\n            first = num\n        elif num > second and num != first:\n            second = num\n    return second\n",
        'test': 'from solution import find_second_largest\n\n\ndef _ref(nums):\n    distinct = sorted(set(nums), reverse=True)\n    return distinct[1] if len(distinct) >= 2 else float("-inf")\n\n\ndef test_matches_reference():\n    cases = [\n        [1, 3, 2, 5, 4],\n        [5, 5, 4, 4, 3],\n        [10, 10, 10, 9],\n        [1, 2],\n        [-3, -1, -2],\n    ]\n    for n in cases:\n        assert find_second_largest(n) == _ref(n)\n\n',
    },
    {
        'task_id': 'task_021',
        'source': 'mutation_exercism',
        'category': 'wrong_variable',
        'difficulty': 'medium',
        'lines_changed': 1,
        'description': 'is_anagram returns True instead of False when lengths differ',
        'buggy': 'def is_anagram(s, t):\n    if len(s) != len(t):\n        return True\n    counts = {}\n    for ch in s:\n        counts[ch] = counts.get(ch, 0) + 1\n    for ch in t:\n        counts[ch] = counts.get(ch, 0) - 1\n    return all(v == 0 for v in counts.values())\n',
        'fixed': 'def is_anagram(s, t):\n    if len(s) != len(t):\n        return False\n    counts = {}\n    for ch in s:\n        counts[ch] = counts.get(ch, 0) + 1\n    for ch in t:\n        counts[ch] = counts.get(ch, 0) - 1\n    return all(v == 0 for v in counts.values())\n',
        'test': 'from collections import Counter\nfrom solution import is_anagram\n\n\ndef test_matches_reference():\n    cases = [\n        ("anagram", "nagaram", True),\n        ("rat", "car", False),\n        ("a", "a", True),\n        ("a", "ab", False),\n        ("", "", True),\n        ("abc", "abcd", False),\n        ("listen", "silent", True),\n        ("aabb", "abab", True),\n        ("aabb", "abbb", False),\n    ]\n    for s, t, expected in cases:\n        assert is_anagram(s, t) is expected\n        # cross-check: anagram iff equal multiset\n        assert is_anagram(s, t) is (Counter(s) == Counter(t))\n\n',
    },
    {
        'task_id': 'task_022',
        'source': 'mutation_exercism',
        'category': 'wrong_variable',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'word_count uses wrong variable name, counting chars instead of words',
        'buggy': 'def word_count(sentence):\n    counts = {}\n    for word in sentence.split():\n        counts[sentence] = counts.get(sentence, 0) + 1\n    return counts\n',
        'fixed': 'def word_count(sentence):\n    counts = {}\n    for word in sentence.split():\n        counts[word] = counts.get(word, 0) + 1\n    return counts\n',
        'test': 'from collections import Counter\nfrom solution import word_count\n\n\ndef test_matches_reference():\n    cases = [\n        "the quick brown fox",\n        "hello world hello",\n        "a a a b b c",\n        "single",\n        "",\n    ]\n    for s in cases:\n        assert word_count(s) == dict(Counter(s.split()))\n\n',
    },
    {
        'task_id': 'task_023',
        'source': 'mutation_exercism',
        'category': 'wrong_variable',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'transpose_matrix swaps matrix[i][j] with matrix[i][j] (no-op) instead of matrix[j][i]',
        'buggy': 'def transpose(matrix):\n    n = len(matrix)\n    for i in range(n):\n        for j in range(i + 1, n):\n            matrix[i][j], matrix[i][j] = matrix[j][i], matrix[i][j]\n    return matrix\n',
        'fixed': 'def transpose(matrix):\n    n = len(matrix)\n    for i in range(n):\n        for j in range(i + 1, n):\n            matrix[i][j], matrix[j][i] = matrix[j][i], matrix[i][j]\n    return matrix\n',
        'test': 'from solution import transpose\n\n\ndef test_matches_reference():\n    cases = [\n        [[1, 2], [3, 4]],\n        [[1, 2, 3], [4, 5, 6], [7, 8, 9]],\n        [[5]],\n        [[1, 0], [0, 1]],\n    ]\n    for m in cases:\n        original = [row[:] for row in m]\n        out = transpose([row[:] for row in m])\n        n = len(original)\n        for i in range(n):\n            for j in range(n):\n                assert out[i][j] == original[j][i]\n\n',
    },
    {
        'task_id': 'task_024',
        'source': 'mutation_exercism',
        'category': 'wrong_variable',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'capitalize_words calls lower() instead of capitalize() on each word',
        'buggy': "def capitalize_words(sentence):\n    return ' '.join(word.lower() for word in sentence.split())\n",
        'fixed': "def capitalize_words(sentence):\n    return ' '.join(word.capitalize() for word in sentence.split())\n",
        'test': 'from solution import capitalize_words\n\n\ndef test_matches_reference():\n    cases = ["hello world", "the quick brown fox", "PYTHON is FUN", "a b c", "single"]\n    for s in cases:\n        assert capitalize_words(s) == " ".join(w.capitalize() for w in s.split())\n\n',
    },
    {
        'task_id': 'task_025',
        'source': 'mutation_exercism',
        'category': 'wrong_variable',
        'difficulty': 'medium',
        'lines_changed': 1,
        'description': 'power function passes exponent as base and base as exponent',
        'buggy': 'def power(base, exponent):\n    result = 1\n    for _ in range(base):\n        result *= exponent\n    return result\n',
        'fixed': 'def power(base, exponent):\n    result = 1\n    for _ in range(exponent):\n        result *= base\n    return result\n',
        'test': 'from solution import power\n\n\ndef test_matches_python_pow():\n    cases = [(2, 0), (2, 1), (2, 5), (3, 4), (5, 2), (0, 5), (1, 100), (7, 3)]\n    for b, e in cases:\n        assert power(b, e) == b ** e\n\n',
    },
    {
        'task_id': 'task_026',
        'source': 'mutation_exercism',
        'category': 'wrong_variable',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'count_vowels checks character against consonants set instead of vowels set',
        'buggy': "def count_vowels(s):\n    consonants = set('bcdfghjklmnpqrstvwxyz')\n    return sum(1 for ch in s.lower() if ch in consonants)\n",
        'fixed': "def count_vowels(s):\n    vowels = set('aeiou')\n    return sum(1 for ch in s.lower() if ch in vowels)\n",
        'test': 'from solution import count_vowels\n\n\ndef _ref(s):\n    return sum(1 for ch in s.lower() if ch in "aeiou")\n\n\ndef test_matches_reference():\n    for s in ["hello", "AEIOU", "rhythm", "", "Programming", "xyz"]:\n        assert count_vowels(s) == _ref(s)\n\n',
    },
    {
        'task_id': 'task_027',
        'source': 'mutation_exercism',
        'category': 'wrong_variable',
        'difficulty': 'medium',
        'lines_changed': 1,
        'description': 'longest_common_prefix checks prefix.startswith(s) instead of s.startswith(prefix)',
        'buggy': "def longest_common_prefix(strs):\n    if not strs:\n        return ''\n    prefix = strs[0]\n    for s in strs[1:]:\n        while not prefix.startswith(s[:len(prefix)]):\n            prefix = prefix[:-1]\n            if not prefix:\n                return ''\n    return prefix\n",
        'fixed': "def longest_common_prefix(strs):\n    if not strs:\n        return ''\n    prefix = strs[0]\n    for s in strs[1:]:\n        while not s.startswith(prefix):\n            prefix = prefix[:-1]\n            if not prefix:\n                return ''\n    return prefix\n",
        'test': 'import os\nfrom solution import longest_common_prefix\n\n\ndef test_matches_os_commonprefix():\n    cases = [\n        ["flower", "flow", "flight"],\n        ["dog", "racecar", "car"],\n        ["interstellar", "interstate", "internal"],\n        ["a"],\n        ["", "abc"],\n        ["same", "same", "same"],\n        ["flower", "fl"],\n        ["abcdef", "abc"],\n        ["prefix", "pre", "prefix"],\n    ]\n    for strs in cases:\n        assert longest_common_prefix(strs) == os.path.commonprefix(strs)\n\n\ndef test_empty_input():\n    assert longest_common_prefix([]) == ""\n',
    },
    {
        'task_id': 'task_028',
        'source': 'mutation_exercism',
        'category': 'missing_check',
        'difficulty': 'easy',
        'lines_changed': 2,
        'description': "safe_divide raises ZeroDivisionError because it doesn't check for zero denominator",
        'buggy': 'def safe_divide(a, b):\n    return a / b\n',
        'fixed': 'def safe_divide(a, b):\n    if b == 0:\n        return None\n    return a / b\n',
        'test': 'from solution import safe_divide\n\n\ndef test_matches_reference():\n    cases = [(10, 2, 5), (7, 0, None), (0, 5, 0), (-6, 3, -2), (1, 0, None)]\n    for a, b, expected in cases:\n        out = safe_divide(a, b)\n        assert out == expected\n\n',
    },
    {
        'task_id': 'task_029',
        'source': 'mutation_exercism',
        'category': 'missing_check',
        'difficulty': 'easy',
        'lines_changed': 2,
        'description': 'list_average raises ZeroDivisionError on empty list instead of returning None',
        'buggy': 'def list_average(nums):\n    return sum(nums) / len(nums)\n',
        'fixed': 'def list_average(nums):\n    if not nums:\n        return None\n    return sum(nums) / len(nums)\n',
        'test': 'from statistics import mean\nfrom solution import list_average\n\n\ndef test_matches_statistics_mean():\n    cases = [[1, 2, 3, 4], [5], [-1, 1], [10, 20, 30], [0, 0, 0]]\n    for nums in cases:\n        assert list_average(nums) == mean(nums)\n\n\ndef test_empty_returns_none():\n    assert list_average([]) is None\n\n',
    },
    {
        'task_id': 'task_030',
        'source': 'mutation_exercism',
        'category': 'missing_check',
        'difficulty': 'easy',
        'lines_changed': 3,
        'description': 'safe_sqrt raises ValueError on negative input instead of returning None',
        'buggy': 'import math\n\ndef safe_sqrt(n):\n    return math.sqrt(n)\n',
        'fixed': 'import math\n\ndef safe_sqrt(n):\n    if n < 0:\n        return None\n    return math.sqrt(n)\n',
        'test': 'import math\nfrom solution import safe_sqrt\n\n\ndef test_matches_math_sqrt():\n    for n in [0, 1, 4, 9, 16, 25, 2, 100]:\n        assert safe_sqrt(n) == math.sqrt(n)\n\n\ndef test_negative_returns_none():\n    for n in [-1, -5, -100]:\n        assert safe_sqrt(n) is None\n\n',
    },
    {
        'task_id': 'task_031',
        'source': 'mutation_exercism',
        'category': 'missing_check',
        'difficulty': 'easy',
        'lines_changed': 3,
        'description': 'stack_peek raises IndexError on empty stack instead of returning None',
        'buggy': 'def stack_peek(stack):\n    return stack[-1]\n',
        'fixed': 'def stack_peek(stack):\n    if not stack:\n        return None\n    return stack[-1]\n',
        'test': 'from solution import stack_peek\n\n\ndef test_matches_reference():\n    for s in [[1], [1, 2, 3], ["a", "b"], [None]]:\n        assert stack_peek(list(s)) == s[-1]\n\n\ndef test_empty_returns_none():\n    assert stack_peek([]) is None\n\n',
    },
    {
        'task_id': 'task_032',
        'source': 'mutation_exercism',
        'category': 'missing_check',
        'difficulty': 'easy',
        'lines_changed': 2,
        'description': 'is_prime returns True for n=1, which is not a prime number',
        'buggy': 'def is_prime(n):\n    if n < 2:\n        return True\n    for i in range(2, int(n**0.5) + 1):\n        if n % i == 0:\n            return False\n    return True\n',
        'fixed': 'def is_prime(n):\n    if n < 2:\n        return False\n    for i in range(2, int(n**0.5) + 1):\n        if n % i == 0:\n            return False\n    return True\n',
        'test': 'from solution import is_prime\n\n\ndef _ref(n):\n    if n < 2:\n        return False\n    return all(n % i for i in range(2, int(n ** 0.5) + 1))\n\n\ndef test_matches_reference():\n    for n in range(-2, 50):\n        assert is_prime(n) == _ref(n)\n\n\ndef test_known_primes():\n    for p in [2, 3, 5, 7, 11, 13, 97, 101]:\n        assert is_prime(p) is True\n\n\ndef test_known_composites():\n    for c in [0, 1, 4, 6, 8, 9, 100]:\n        assert is_prime(c) is False\n\n',
    },
    {
        'task_id': 'task_033',
        'source': 'mutation_exercism',
        'category': 'missing_check',
        'difficulty': 'easy',
        'lines_changed': 3,
        'description': "factorial doesn't handle n=0, returning wrong result due to empty range",
        'buggy': 'def factorial(n):\n    result = 0\n    for i in range(1, n + 1):\n        result *= i\n    return result\n',
        'fixed': 'def factorial(n):\n    result = 1\n    for i in range(1, n + 1):\n        result *= i\n    return result\n',
        'test': 'import math\nfrom solution import factorial\n\n\ndef test_matches_math_factorial():\n    for n in range(0, 10):\n        assert factorial(n) == math.factorial(n)\n\n',
    },
    {
        'task_id': 'task_034',
        'source': 'mutation_exercism',
        'category': 'missing_check',
        'difficulty': 'medium',
        'lines_changed': 3,
        'description': 'count_digits returns 0 for n=0 instead of 1',
        'buggy': 'def count_digits(n):\n    n = abs(n)\n    count = 0\n    while n > 0:\n        n //= 10\n        count += 1\n    return count\n',
        'fixed': 'def count_digits(n):\n    n = abs(n)\n    if n == 0:\n        return 1\n    count = 0\n    while n > 0:\n        n //= 10\n        count += 1\n    return count\n',
        'test': 'from solution import count_digits\n\n\ndef _ref(n):\n    return len(str(abs(n))) if n != 0 else 1\n\n\ndef test_matches_reference():\n    for n in [0, 1, 9, 10, 99, 100, 12345, -7, -100]:\n        assert count_digits(n) == _ref(n)\n\n',
    },
    {
        'task_id': 'task_035',
        'source': 'mutation_exercism',
        'category': 'missing_check',
        'difficulty': 'easy',
        'lines_changed': 3,
        'description': 'first_element raises IndexError on empty list instead of returning None',
        'buggy': 'def first_element(lst):\n    return lst[0]\n',
        'fixed': 'def first_element(lst):\n    if not lst:\n        return None\n    return lst[0]\n',
        'test': 'from solution import first_element\n\n\ndef test_matches_reference():\n    for lst in [[1, 2, 3], ["a"], [None, 2], [0]]:\n        assert first_element(list(lst)) == lst[0]\n\n\ndef test_empty_returns_none():\n    assert first_element([]) is None\n\n',
    },
    {
        'task_id': 'task_036',
        'source': 'mutation_exercism',
        'category': 'missing_check',
        'difficulty': 'medium',
        'lines_changed': 3,
        'description': 'max_in_matrix crashes on empty matrix instead of returning None',
        'buggy': 'def max_in_matrix(matrix):\n    return max(max(row) for row in matrix)\n',
        'fixed': 'def max_in_matrix(matrix):\n    if not matrix or not matrix[0]:\n        return None\n    return max(max(row) for row in matrix)\n',
        'test': 'from solution import max_in_matrix\n\n\ndef _ref(m):\n    if not m or not m[0]:\n        return None\n    return max(x for row in m for x in row)\n\n\ndef test_matches_reference():\n    cases = [\n        [[1, 2], [3, 4]],\n        [[7]],\n        [[-5, -3], [-10, -1]],\n        [],\n        [[]],\n        [[1, 2, 3], [4, 5, 6], [7, 8, 9]],\n    ]\n    for m in cases:\n        assert max_in_matrix(m) == _ref(m)\n\n',
    },
    {
        'task_id': 'task_037',
        'source': 'mutation_exercism',
        'category': 'missing_check',
        'difficulty': 'easy',
        'lines_changed': 2,
        'description': 'remove_item raises ValueError when item not in list instead of returning list unchanged',
        'buggy': 'def remove_item(lst, item):\n    lst = list(lst)\n    lst.remove(item)\n    return lst\n',
        'fixed': 'def remove_item(lst, item):\n    lst = list(lst)\n    if item in lst:\n        lst.remove(item)\n    return lst\n',
        'test': 'from solution import remove_item\n\n\ndef test_matches_reference():\n    cases = [\n        ([1, 2, 3], 2, [1, 3]),\n        ([1, 2, 3], 9, [1, 2, 3]),\n        ([1, 1, 2], 1, [1, 2]),\n        ([], 5, []),\n    ]\n    for lst, item, expected in cases:\n        out = remove_item(list(lst), item)\n        assert out == expected\n\n',
    },
    {
        'task_id': 'task_038',
        'source': 'mutation_exercism',
        'category': 'missing_check',
        'difficulty': 'easy',
        'lines_changed': 2,
        'description': 'safe_log raises ValueError on non-positive input instead of returning None',
        'buggy': 'import math\n\ndef safe_log(n):\n    return math.log(n)\n',
        'fixed': 'import math\n\ndef safe_log(n):\n    if n <= 0:\n        return None\n    return math.log(n)\n',
        'test': 'import math\nfrom solution import safe_log\n\n\ndef test_matches_math_log():\n    for n in [1, 2, math.e, 10, 100]:\n        assert safe_log(n) == math.log(n)\n\n\ndef test_non_positive_returns_none():\n    for n in [0, -1, -10]:\n        assert safe_log(n) is None\n\n',
    },
    {
        'task_id': 'task_039',
        'source': 'mutation_exercism',
        'category': 'missing_check',
        'difficulty': 'medium',
        'lines_changed': 2,
        'description': 'nested_list_depth misses empty list base case, returning 1 instead of 0',
        'buggy': 'def list_depth(lst):\n    if not isinstance(lst, list):\n        return 0\n    return 1 + max(list_depth(item) for item in lst)\n',
        'fixed': 'def list_depth(lst):\n    if not isinstance(lst, list):\n        return 0\n    if not lst:\n        return 1\n    return 1 + max(list_depth(item) for item in lst)\n',
        'test': 'from solution import list_depth\n\n\ndef _ref(lst):\n    if not isinstance(lst, list):\n        return 0\n    if not lst:\n        return 1\n    return 1 + max(_ref(x) for x in lst)\n\n\ndef test_matches_reference():\n    cases = [\n        [1, 2, 3],\n        [],\n        [[1, 2], [3]],\n        [1, [2, [3, [4]]]],\n        [[]],\n    ]\n    for lst in cases:\n        assert list_depth(lst) == _ref(lst)\n\n',
    },
    {
        'task_id': 'task_040',
        'source': 'mutation_exercism',
        'category': 'missing_check',
        'difficulty': 'easy',
        'lines_changed': 2,
        'description': 'safe_pop raises IndexError on empty list instead of returning None',
        'buggy': 'def safe_pop(lst):\n    return lst.pop()\n',
        'fixed': 'def safe_pop(lst):\n    if not lst:\n        return None\n    return lst.pop()\n',
        'test': 'from solution import safe_pop\n\n\ndef test_matches_reference():\n    for lst in [[1], [1, 2, 3], ["a", "b"]]:\n        copy = list(lst)\n        assert safe_pop(copy) == lst[-1]\n\n\ndef test_empty_returns_none():\n    assert safe_pop([]) is None\n\n',
    },
    {
        'task_id': 'task_041',
        'source': 'mutation_exercism',
        'category': 'missing_check',
        'difficulty': 'easy',
        'lines_changed': 2,
        'description': 'dict_get raises KeyError when key is missing instead of returning a default value',
        'buggy': 'def safe_dict_get(d, key, default=None):\n    return d[key]\n',
        'fixed': 'def safe_dict_get(d, key, default=None):\n    return d.get(key, default)\n',
        'test': 'from solution import safe_dict_get\n\n\ndef test_matches_dict_get():\n    d = {"a": 1, "b": 2}\n    assert safe_dict_get(d, "a") == 1\n    assert safe_dict_get(d, "missing") is None\n    assert safe_dict_get(d, "missing", default=42) == 42\n    assert safe_dict_get({}, "x") is None\n\n',
    },
    {
        'task_id': 'task_042',
        'source': 'mutation_exercism',
        'category': 'missing_check',
        'difficulty': 'easy',
        'lines_changed': 2,
        'description': 'parse_int wraps result in abs(), turning negative numbers positive',
        'buggy': 'def parse_int(s):\n    return abs(int(s.strip()))\n',
        'fixed': 'def parse_int(s):\n    return int(s.strip())\n',
        'test': 'from solution import parse_int\n\n\ndef test_matches_int():\n    cases = ["42", "-5", "  10  ", "0", "  -7", "100"]\n    for s in cases:\n        assert parse_int(s) == int(s.strip())\n\n',
    },
    {
        'task_id': 'task_043',
        'source': 'mutation_exercism',
        'category': 'logic_error',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'max_subarray uses min() instead of max() to update the running maximum',
        'buggy': 'def max_subarray(nums):\n    max_sum = current = nums[0]\n    for num in nums[1:]:\n        current = min(current + num, num)\n        max_sum = max(max_sum, current)\n    return max_sum\n',
        'fixed': 'def max_subarray(nums):\n    max_sum = current = nums[0]\n    for num in nums[1:]:\n        current = max(current + num, num)\n        max_sum = max(max_sum, current)\n    return max_sum\n',
        'test': 'from solution import max_subarray\n\n\ndef _ref(nums):\n    best = cur = nums[0]\n    for x in nums[1:]:\n        cur = max(x, cur + x)\n        best = max(best, cur)\n    return best\n\n\ndef test_matches_reference():\n    cases = [\n        [-2, 1, -3, 4, -1, 2, 1, -5, 4],\n        [1],\n        [-1, -2, -3],\n        [5, 4, -1, 7, 8],\n        [3, -2, 5, -1],\n    ]\n    for nums in cases:\n        assert max_subarray(nums) == _ref(nums)\n\n',
    },
    {
        'task_id': 'task_044',
        'source': 'mutation_exercism',
        'category': 'logic_error',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'is_sorted returns False for arrays with equal consecutive elements due to wrong operator',
        'buggy': 'def is_sorted(arr):\n    for i in range(len(arr) - 1):\n        if arr[i] >= arr[i + 1]:\n            return False\n    return True\n',
        'fixed': 'def is_sorted(arr):\n    for i in range(len(arr) - 1):\n        if arr[i] > arr[i + 1]:\n            return False\n    return True\n',
        'test': 'from solution import is_sorted\n\n\ndef _ref(arr):\n    return all(arr[i] <= arr[i + 1] for i in range(len(arr) - 1))\n\n\ndef test_matches_reference():\n    cases = [\n        [1, 2, 3], [3, 2, 1], [1, 1, 2, 3], [1], [], [5, 5, 5], [1, 3, 2],\n    ]\n    for arr in cases:\n        assert is_sorted(arr) is _ref(arr)\n\n',
    },
    {
        'task_id': 'task_045',
        'source': 'mutation_exercism',
        'category': 'logic_error',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'count_evens checks odd condition instead of even condition',
        'buggy': 'def count_evens(nums):\n    return sum(1 for n in nums if n % 2 != 0)\n',
        'fixed': 'def count_evens(nums):\n    return sum(1 for n in nums if n % 2 == 0)\n',
        'test': 'from solution import count_evens\n\n\ndef _ref(nums):\n    return sum(1 for n in nums if n % 2 == 0)\n\n\ndef test_matches_reference():\n    for nums in [[1, 2, 3, 4], [1, 3, 5], [2, 4, 6], [], [-2, -1, 0, 1]]:\n        assert count_evens(nums) == _ref(nums)\n\n',
    },
    {
        'task_id': 'task_046',
        'source': 'mutation_exercism',
        'category': 'logic_error',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'factorial uses addition instead of multiplication',
        'buggy': 'def factorial(n):\n    result = 1\n    for i in range(1, n + 1):\n        result += i\n    return result\n',
        'fixed': 'def factorial(n):\n    result = 1\n    for i in range(1, n + 1):\n        result *= i\n    return result\n',
        'test': 'import math\nfrom solution import factorial\n\n\ndef test_matches_math_factorial():\n    for n in range(0, 10):\n        assert factorial(n) == math.factorial(n)\n\n',
    },
    {
        'task_id': 'task_047',
        'source': 'mutation_exercism',
        'category': 'logic_error',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'sum_of_squares sums then squares instead of squaring each element then summing',
        'buggy': 'def sum_of_squares(nums):\n    return sum(nums) ** 2\n',
        'fixed': 'def sum_of_squares(nums):\n    return sum(n ** 2 for n in nums)\n',
        'test': 'from solution import sum_of_squares\n\n\ndef _ref(nums):\n    return sum(n ** 2 for n in nums)\n\n\ndef test_matches_reference():\n    cases = [[1, 2, 3], [0, 0], [-1, 1], [], [5], [2, 3, 4]]\n    for nums in cases:\n        assert sum_of_squares(nums) == _ref(nums)\n\n',
    },
    {
        'task_id': 'task_048',
        'source': 'mutation_exercism',
        'category': 'logic_error',
        'difficulty': 'medium',
        'lines_changed': 1,
        'description': "is_palindrome doesn't lowercase before comparing, failing on mixed-case palindromes",
        'buggy': "def is_palindrome(s):\n    cleaned = ''.join(ch for ch in s if ch.isalnum())\n    return cleaned == cleaned[::-1]\n",
        'fixed': "def is_palindrome(s):\n    cleaned = ''.join(ch.lower() for ch in s if ch.isalnum())\n    return cleaned == cleaned[::-1]\n",
        'test': 'from solution import is_palindrome\n\n\ndef _ref(s):\n    cleaned = "".join(ch.lower() for ch in s if ch.isalnum())\n    return cleaned == cleaned[::-1]\n\n\ndef test_matches_reference():\n    cases = [\n        "A man a plan a canal Panama",\n        "race a car",\n        "",\n        "ab",\n        "aA",\n        "No lemon, no melon",\n        "Hello",\n    ]\n    for s in cases:\n        assert is_palindrome(s) is _ref(s)\n\n',
    },
    {
        'task_id': 'task_049',
        'source': 'mutation_exercism',
        'category': 'logic_error',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'find_max initializes max_val to 0, failing for all-negative arrays',
        'buggy': 'def find_max(nums):\n    max_val = 0\n    for num in nums:\n        if num > max_val:\n            max_val = num\n    return max_val\n',
        'fixed': 'def find_max(nums):\n    max_val = nums[0]\n    for num in nums[1:]:\n        if num > max_val:\n            max_val = num\n    return max_val\n',
        'test': 'from solution import find_max\n\n\ndef test_matches_builtin_max():\n    cases = [[1, 2, 3], [-1, -2, -3], [5], [-100, -200, -50], [0, 0, 0], [3, 1, 4, 1, 5]]\n    for nums in cases:\n        assert find_max(nums) == max(nums)\n\n',
    },
    {
        'task_id': 'task_050',
        'source': 'mutation_exercism',
        'category': 'logic_error',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'find_min initializes min_val to 0 instead of first element, failing for all-positive arrays > 0',
        'buggy': 'def find_min(nums):\n    min_val = 0\n    for num in nums:\n        if num < min_val:\n            min_val = num\n    return min_val\n',
        'fixed': 'def find_min(nums):\n    min_val = nums[0]\n    for num in nums[1:]:\n        if num < min_val:\n            min_val = num\n    return min_val\n',
        'test': 'from solution import find_min\n\n\ndef test_matches_builtin_min():\n    cases = [[1, 2, 3], [-1, -2, -3], [5], [100, 200, 50], [0, 0, 0], [3, 1, 4, 1, 5]]\n    for nums in cases:\n        assert find_min(nums) == min(nums)\n\n',
    },
    {
        'task_id': 'task_051',
        'source': 'mutation_exercism',
        'category': 'logic_error',
        'difficulty': 'medium',
        'lines_changed': 1,
        'description': 'fizzbuzz checks multiples of 3 and 5 before checking 15, missing FizzBuzz output',
        'buggy': "def fizzbuzz(n):\n    result = []\n    for i in range(1, n + 1):\n        if i % 3 == 0:\n            result.append('Fizz')\n        elif i % 5 == 0:\n            result.append('Buzz')\n        elif i % 15 == 0:\n            result.append('FizzBuzz')\n        else:\n            result.append(str(i))\n    return result\n",
        'fixed': "def fizzbuzz(n):\n    result = []\n    for i in range(1, n + 1):\n        if i % 15 == 0:\n            result.append('FizzBuzz')\n        elif i % 3 == 0:\n            result.append('Fizz')\n        elif i % 5 == 0:\n            result.append('Buzz')\n        else:\n            result.append(str(i))\n    return result\n",
        'test': 'from solution import fizzbuzz\n\n\ndef _ref(n):\n    out = []\n    for i in range(1, n + 1):\n        if i % 15 == 0:\n            out.append("FizzBuzz")\n        elif i % 3 == 0:\n            out.append("Fizz")\n        elif i % 5 == 0:\n            out.append("Buzz")\n        else:\n            out.append(str(i))\n    return out\n\n\ndef test_matches_reference():\n    for n in [1, 5, 15, 16, 30, 100]:\n        assert fizzbuzz(n) == _ref(n)\n\n',
    },
    {
        'task_id': 'task_052',
        'source': 'mutation_exercism',
        'category': 'logic_error',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'remove_vowels keeps vowels and removes consonants due to inverted condition',
        'buggy': "def remove_vowels(s):\n    vowels = set('aeiouAEIOU')\n    return ''.join(ch for ch in s if ch in vowels)\n",
        'fixed': "def remove_vowels(s):\n    vowels = set('aeiouAEIOU')\n    return ''.join(ch for ch in s if ch not in vowels)\n",
        'test': 'from solution import remove_vowels\n\n\ndef _ref(s):\n    return "".join(ch for ch in s if ch not in "aeiouAEIOU")\n\n\ndef test_matches_reference():\n    for s in ["hello", "AEIOU", "rhythm", "", "Programming", "xyz", "Hi There!"]:\n        assert remove_vowels(s) == _ref(s)\n\n',
    },
    {
        'task_id': 'task_053',
        'source': 'mutation_exercism',
        'category': 'logic_error',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'frequency_count uses != instead of == when counting target, counting everything else',
        'buggy': 'def count_occurrences(lst, target):\n    return sum(1 for item in lst if item != target)\n',
        'fixed': 'def count_occurrences(lst, target):\n    return sum(1 for item in lst if item == target)\n',
        'test': 'from solution import count_occurrences\n\n\ndef test_matches_list_count():\n    cases = [\n        ([1, 2, 3, 2, 1], 2),\n        ([1, 1, 1], 1),\n        (["a", "b", "a"], "a"),\n        ([], 5),\n        ([1, 2, 3], 9),\n    ]\n    for lst, target in cases:\n        assert count_occurrences(lst, target) == lst.count(target)\n\n',
    },
    {
        'task_id': 'task_054',
        'source': 'mutation_exercism',
        'category': 'logic_error',
        'difficulty': 'medium',
        'lines_changed': 1,
        'description': 'check_balanced uses wrong counter update: increments for ) and decrements for (',
        'buggy': "def is_balanced(s):\n    count = 0\n    for ch in s:\n        if ch == ')':\n            count += 1\n        elif ch == '(':\n            count -= 1\n        if count < 0:\n            return False\n    return count == 0\n",
        'fixed': "def is_balanced(s):\n    count = 0\n    for ch in s:\n        if ch == '(':\n            count += 1\n        elif ch == ')':\n            count -= 1\n        if count < 0:\n            return False\n    return count == 0\n",
        'test': 'from solution import is_balanced\n\n\ndef _ref(s):\n    c = 0\n    for ch in s:\n        if ch == "(":\n            c += 1\n        elif ch == ")":\n            c -= 1\n        if c < 0:\n            return False\n    return c == 0\n\n\ndef test_matches_reference():\n    cases = ["()", "(())", "()()", "(()", "())", ")(", "", "((()))", "(()())"]\n    for s in cases:\n        assert is_balanced(s) is _ref(s)\n\n',
    },
    {
        'task_id': 'task_055',
        'source': 'mutation_exercism',
        'category': 'logic_error',
        'difficulty': 'medium',
        'lines_changed': 1,
        'description': 'gcd_recursive uses integer division (a//b) instead of modulo (a%b)',
        'buggy': 'def gcd_recursive(a, b):\n    if b == 0:\n        return a\n    return gcd_recursive(b, a // b)\n',
        'fixed': 'def gcd_recursive(a, b):\n    if b == 0:\n        return a\n    return gcd_recursive(b, a % b)\n',
        'test': 'import math\nfrom solution import gcd_recursive\n\n\ndef test_matches_math_gcd():\n    pairs = [(48, 18), (100, 75), (17, 13), (1, 1), (12, 0), (270, 192)]\n    for a, b in pairs:\n        assert gcd_recursive(a, b) == math.gcd(a, b)\n\n',
    },
    {
        'task_id': 'task_056',
        'source': 'mutation_exercism',
        'category': 'logic_error',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'sort_by_length sorts by negative length, giving descending order instead of ascending',
        'buggy': 'def sort_by_length(words):\n    return sorted(words, key=lambda w: -len(w))\n',
        'fixed': 'def sort_by_length(words):\n    return sorted(words, key=len)\n',
        'test': 'from solution import sort_by_length\n\n\ndef test_sorted_by_length_ascending():\n    cases = [\n        ["banana", "apple", "kiwi", "fig"],\n        ["a", "ab", "abc"],\n        [],\n        ["same", "size", "tens"],\n    ]\n    for words in cases:\n        out = sort_by_length(list(words))\n        assert out == sorted(words, key=len)\n\n',
    },
    {
        'task_id': 'task_057',
        'source': 'mutation_exercism',
        'category': 'logic_error',
        'difficulty': 'medium',
        'lines_changed': 1,
        'description': 'two_sum_exists adds complement to seen set instead of num, breaking lookup',
        'buggy': 'def two_sum_exists(nums, target):\n    seen = set()\n    for num in nums:\n        if target - num in seen:\n            return True\n        seen.add(target - num)\n    return False\n',
        'fixed': 'def two_sum_exists(nums, target):\n    seen = set()\n    for num in nums:\n        if target - num in seen:\n            return True\n        seen.add(num)\n    return False\n',
        'test': 'from solution import two_sum_exists\n\n\ndef _ref(nums, target):\n    seen = set()\n    for n in nums:\n        if target - n in seen:\n            return True\n        seen.add(n)\n    return False\n\n\ndef test_matches_reference():\n    cases = [\n        ([1, 2, 3, 4], 5),\n        ([1, 2, 3], 7),\n        ([3, 3], 6),\n        ([], 5),\n        ([5], 5),\n        ([1, 5, 9, 2], 11),\n    ]\n    for nums, t in cases:\n        assert two_sum_exists(nums, t) is _ref(nums, t)\n\n',
    },
    {
        'task_id': 'task_058',
        'source': 'mutation_exercism',
        'category': 'logic_error',
        'difficulty': 'medium',
        'lines_changed': 1,
        'description': 'flatten uses += [sublist] creating nested results instead of result.extend()',
        'buggy': 'def flatten(lst):\n    result = []\n    for item in lst:\n        if isinstance(item, list):\n            result += [flatten(item)]\n        else:\n            result.append(item)\n    return result\n',
        'fixed': 'def flatten(lst):\n    result = []\n    for item in lst:\n        if isinstance(item, list):\n            result.extend(flatten(item))\n        else:\n            result.append(item)\n    return result\n',
        'test': 'from solution import flatten\n\n\ndef _ref(lst):\n    out = []\n    for x in lst:\n        if isinstance(x, list):\n            out.extend(_ref(x))\n        else:\n            out.append(x)\n    return out\n\n\ndef test_matches_reference():\n    cases = [\n        [1, [2, [3, [4]]]],\n        [[1, 2], [3, 4]],\n        [],\n        [1, 2, 3],\n        [[], [1], [], [2, [3]]],\n    ]\n    for lst in cases:\n        assert flatten(lst) == _ref(lst)\n\n',
    },
    {
        'task_id': 'task_059',
        'source': 'mutation_exercism',
        'category': 'logic_error',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': "and_or_confusion: uses 'and' where 'or' is needed in leap year check",
        'buggy': 'def is_leap_year(year):\n    return (year % 4 == 0 and year % 100 != 0) and (year % 400 == 0)\n',
        'fixed': 'def is_leap_year(year):\n    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)\n',
        'test': 'import calendar\nfrom solution import is_leap_year\n\n\ndef test_matches_calendar_isleap():\n    for year in [1900, 2000, 2004, 2020, 2021, 2100, 2400, 1, 4, 100, 400]:\n        assert is_leap_year(year) is calendar.isleap(year)\n\n',
    },
    {
        'task_id': 'task_060',
        'source': 'mutation_exercism',
        'category': 'logic_error',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'product_of_list uses sum() instead of computing the product',
        'buggy': 'def product_of_list(nums):\n    result = 0\n    for n in nums:\n        result += n\n    return result\n',
        'fixed': 'def product_of_list(nums):\n    result = 1\n    for n in nums:\n        result *= n\n    return result\n',
        'test': 'import math\nfrom solution import product_of_list\n\n\ndef test_matches_math_prod():\n    cases = [[1, 2, 3], [5], [2, 0, 5], [-1, 2, -3], [10, 10], [1]]\n    for nums in cases:\n        assert product_of_list(nums) == math.prod(nums)\n\n',
    },
    {
        'task_id': 'task_061',
        'source': 'mutation_exercism',
        'category': 'type_error',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'join_numbers fails with TypeError trying to join integers without converting to strings',
        'buggy': "def join_numbers(nums, sep=', '):\n    return sep.join(nums)\n",
        'fixed': "def join_numbers(nums, sep=', '):\n    return sep.join(str(n) for n in nums)\n",
        'test': 'from solution import join_numbers\n\n\ndef test_matches_reference():\n    cases = [\n        ([1, 2, 3], ", "),\n        ([10, 20], "-"),\n        ([], ", "),\n        ([42], ", "),\n    ]\n    for nums, sep in cases:\n        assert join_numbers(nums, sep) == sep.join(str(n) for n in nums)\n\n\ndef test_default_separator():\n    assert join_numbers([1, 2, 3]) == "1, 2, 3"\n\n',
    },
    {
        'task_id': 'task_062',
        'source': 'mutation_exercism',
        'category': 'type_error',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'integer_average uses integer division (//) instead of float division, truncating result',
        'buggy': 'def average(nums):\n    return sum(nums) // len(nums)\n',
        'fixed': 'def average(nums):\n    return sum(nums) / len(nums)\n',
        'test': 'from statistics import mean\nfrom solution import average\n\n\ndef test_returns_float_mean():\n    cases = [[1, 2, 3], [10, 20], [5], [-1, 1, 0]]\n    for nums in cases:\n        out = average(nums)\n        assert out == mean(nums)\n        assert isinstance(out, float)\n\n',
    },
    {
        'task_id': 'task_063',
        'source': 'mutation_exercism',
        'category': 'type_error',
        'difficulty': 'medium',
        'lines_changed': 1,
        'description': 'compare_number_strings compares string lexicographically instead of numerically',
        'buggy': 'def max_number_string(nums):\n    return max(nums)\n',
        'fixed': 'def max_number_string(nums):\n    return max(nums, key=int)\n',
        'test': 'from solution import max_number_string\n\n\ndef test_matches_numeric_max():\n    cases = [["10", "9", "100"], ["5", "5"], ["-3", "2", "-10"], ["100"]]\n    for nums in cases:\n        assert max_number_string(nums) == max(nums, key=int)\n\n',
    },
    {
        'task_id': 'task_064',
        'source': 'mutation_exercism',
        'category': 'type_error',
        'difficulty': 'easy',
        'lines_changed': 2,
        'description': 'sum_with_initial passes wrong type to sum(): sum(list, list) instead of sum(list, int)',
        'buggy': 'def sum_with_initial(nums, initial):\n    return sum(nums, [initial])\n',
        'fixed': 'def sum_with_initial(nums, initial):\n    return sum(nums, initial)\n',
        'test': 'from solution import sum_with_initial\n\n\ndef test_matches_builtin_sum():\n    cases = [([1, 2, 3], 0), ([1, 2, 3], 10), ([], 5), ([5], -2)]\n    for nums, init in cases:\n        assert sum_with_initial(nums, init) == sum(nums, init)\n\n',
    },
    {
        'task_id': 'task_065',
        'source': 'mutation_exercism',
        'category': 'type_error',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'number_to_string uses int() instead of str() when converting number',
        'buggy': 'def number_to_string(n):\n    return int(n)\n',
        'fixed': 'def number_to_string(n):\n    return str(n)\n',
        'test': 'from solution import number_to_string\n\n\ndef test_matches_str():\n    for n in [0, 1, -5, 100, 12345, -999]:\n        out = number_to_string(n)\n        assert out == str(n)\n        assert isinstance(out, str)\n\n',
    },
    {
        'task_id': 'task_066',
        'source': 'mutation_exercism',
        'category': 'type_error',
        'difficulty': 'medium',
        'lines_changed': 1,
        'description': 'list_to_string uses str(list) instead of joining the list elements',
        'buggy': 'def list_to_string(lst):\n    return str(lst)\n',
        'fixed': "def list_to_string(lst):\n    return ''.join(str(x) for x in lst)\n",
        'test': 'from solution import list_to_string\n\n\ndef test_matches_reference():\n    cases = [[1, 2, 3], ["a", "b", "c"], [], [42], [1, "a", 2]]\n    for lst in cases:\n        assert list_to_string(lst) == "".join(str(x) for x in lst)\n\n',
    },
    {
        'task_id': 'task_067',
        'source': 'mutation_exercism',
        'category': 'type_error',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'float_comparison uses == for float comparison, failing due to floating point precision',
        'buggy': 'def is_close_to_zero(x, tolerance=1e-9):\n    return x == 0.0\n',
        'fixed': 'def is_close_to_zero(x, tolerance=1e-9):\n    return abs(x) < tolerance\n',
        'test': 'from solution import is_close_to_zero\n\n\ndef test_within_default_tolerance():\n    assert is_close_to_zero(0.0) is True\n    assert is_close_to_zero(1e-12) is True\n    assert is_close_to_zero(-1e-12) is True\n\n\ndef test_outside_tolerance():\n    assert is_close_to_zero(1e-3) is False\n    assert is_close_to_zero(-0.5) is False\n    assert is_close_to_zero(1.0) is False\n\n\ndef test_custom_tolerance():\n    assert is_close_to_zero(0.001, tolerance=0.01) is True\n    assert is_close_to_zero(0.1, tolerance=0.01) is False\n\n',
    },
    {
        'task_id': 'task_068',
        'source': 'mutation_exercism',
        'category': 'type_error',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'set_difference uses list comprehension with wrong operator instead of set subtraction',
        'buggy': 'def set_difference(a, b):\n    return list(set(a) and set(b))\n',
        'fixed': 'def set_difference(a, b):\n    return sorted(set(a) - set(b))\n',
        'test': 'from solution import set_difference\n\n\ndef test_matches_set_difference():\n    cases = [\n        ([1, 2, 3], [2, 3, 4]),\n        ([1, 2, 3], []),\n        ([], [1, 2]),\n        ([1, 1, 2, 2], [2]),\n        ([5, 4, 3, 2, 1], [3, 1]),\n    ]\n    for a, b in cases:\n        assert set_difference(a, b) == sorted(set(a) - set(b))\n\n',
    },
    {
        'task_id': 'task_069',
        'source': 'mutation_exercism',
        'category': 'type_error',
        'difficulty': 'medium',
        'lines_changed': 1,
        'description': 'dict_values_sum sums dictionary keys instead of values',
        'buggy': 'def sum_values(d):\n    return sum(d.keys())\n',
        'fixed': 'def sum_values(d):\n    return sum(d.values())\n',
        'test': 'from solution import sum_values\n\n\ndef test_sums_values_not_keys():\n    cases = [\n        {"a": 1, "b": 2, "c": 3},\n        {1: 10, 2: 20},\n        {},\n        {"x": 100},\n        {"a": -1, "b": 1},\n    ]\n    for d in cases:\n        assert sum_values(d) == sum(d.values())\n\n',
    },
    {
        'task_id': 'task_070',
        'source': 'mutation_exercism',
        'category': 'type_error',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'type_check uses type() == instead of isinstance(), failing for subclasses',
        'buggy': 'def is_integer(x):\n    return type(x) == int\n',
        'fixed': 'def is_integer(x):\n    return isinstance(x, int)\n',
        'test': 'from solution import is_integer\n\n\ndef test_matches_isinstance_int():\n    samples = [5, 0, -3, 5.0, "5", True, False, None, [], 3.14]\n    for x in samples:\n        assert is_integer(x) is isinstance(x, int)\n\n',
    },
    {
        'task_id': 'task_071',
        'source': 'mutation_exercism',
        'category': 'api_misuse',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'sort_in_place discards return value of list.sort(), returning None',
        'buggy': 'def sorted_copy(lst):\n    return lst.sort()\n',
        'fixed': 'def sorted_copy(lst):\n    return sorted(lst)\n',
        'test': 'from solution import sorted_copy\n\n\ndef test_returns_sorted_copy():\n    cases = [[3, 1, 2], [], [1], [5, 5, 5], [-3, 0, 3, -1]]\n    for lst in cases:\n        original = list(lst)\n        out = sorted_copy(list(lst))\n        assert out == sorted(original)\n        assert out is not None\n\n',
    },
    {
        'task_id': 'task_072',
        'source': 'mutation_exercism',
        'category': 'api_misuse',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'append_list uses append(list) adding list as single element instead of extend(list)',
        'buggy': 'def combine_lists(a, b):\n    result = list(a)\n    result.append(b)\n    return result\n',
        'fixed': 'def combine_lists(a, b):\n    result = list(a)\n    result.extend(b)\n    return result\n',
        'test': 'from solution import combine_lists\n\n\ndef test_concatenates_elements():\n    cases = [\n        ([1, 2], [3, 4]),\n        ([], [1]),\n        ([1], []),\n        ([], []),\n        (["a"], ["b", "c"]),\n    ]\n    for a, b in cases:\n        assert combine_lists(list(a), list(b)) == list(a) + list(b)\n\n',
    },
    {
        'task_id': 'task_073',
        'source': 'mutation_exercism',
        'category': 'api_misuse',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'zip_unequal drops elements from longer list by using zip instead of zip_longest',
        'buggy': 'def zip_fill(a, b, fill=None):\n    return list(zip(a, b))\n',
        'fixed': 'from itertools import zip_longest\n\ndef zip_fill(a, b, fill=None):\n    return list(zip_longest(a, b, fillvalue=fill))\n',
        'test': 'from itertools import zip_longest\nfrom solution import zip_fill\n\n\ndef test_matches_zip_longest():\n    cases = [\n        ([1, 2, 3], ["a", "b"]),\n        ([1], ["a", "b", "c"]),\n        ([], [1, 2]),\n        ([1, 2], [3, 4]),\n    ]\n    for a, b in cases:\n        assert zip_fill(a, b) == list(zip_longest(a, b, fillvalue=None))\n\n\ndef test_custom_fill():\n    assert zip_fill([1, 2], ["a"], fill="X") == list(zip_longest([1, 2], ["a"], fillvalue="X"))\n\n',
    },
    {
        'task_id': 'task_074',
        'source': 'mutation_exercism',
        'category': 'api_misuse',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'dict_setdefault uses assignment instead of setdefault, overwriting existing keys',
        'buggy': 'def group_by_length(words):\n    groups = {}\n    for word in words:\n        key = len(word)\n        groups[key] = [word]\n    return groups\n',
        'fixed': 'def group_by_length(words):\n    groups = {}\n    for word in words:\n        key = len(word)\n        groups.setdefault(key, []).append(word)\n    return groups\n',
        'test': 'from solution import group_by_length\n\n\ndef _ref(words):\n    out = {}\n    for w in words:\n        out.setdefault(len(w), []).append(w)\n    return out\n\n\ndef test_matches_reference():\n    cases = [\n        ["a", "bb", "cc", "ddd"],\n        ["apple", "banana", "kiwi", "fig", "pear"],\n        [],\n        ["x"],\n    ]\n    for words in cases:\n        assert group_by_length(words) == _ref(words)\n\n',
    },
    {
        'task_id': 'task_075',
        'source': 'mutation_exercism',
        'category': 'api_misuse',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': "string_strip strips wrong chars: strips 'ing' chars individually instead of the suffix",
        'buggy': "def remove_suffix_ing(word):\n    return word.strip('ing')\n",
        'fixed': "def remove_suffix_ing(word):\n    if word.endswith('ing'):\n        return word[:-3]\n    return word\n",
        'test': 'from solution import remove_suffix_ing\n\n\ndef _ref(word):\n    return word[:-3] if word.endswith("ing") else word\n\n\ndef test_matches_reference():\n    cases = ["running", "sing", "ing", "ringing", "running and jumping", "test", "go", "ng"]\n    for w in cases:\n        assert remove_suffix_ing(w) == _ref(w)\n\n',
    },
    {
        'task_id': 'task_076',
        'source': 'mutation_exercism',
        'category': 'api_misuse',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'set_add_list uses set.add(list) raising TypeError instead of set.update(list)',
        'buggy': 'def add_elements_to_set(s, elements):\n    s = set(s)\n    s.add(elements)\n    return s\n',
        'fixed': 'def add_elements_to_set(s, elements):\n    s = set(s)\n    s.update(elements)\n    return s\n',
        'test': 'from solution import add_elements_to_set\n\n\ndef test_adds_each_element():\n    cases = [\n        ({1, 2}, [3, 4]),\n        (set(), [1, 2, 3]),\n        ({1}, []),\n        ({1, 2}, [2, 3]),\n    ]\n    for s, elems in cases:\n        out = add_elements_to_set(set(s), list(elems))\n        assert out == set(s) | set(elems)\n\n',
    },
    {
        'task_id': 'task_077',
        'source': 'mutation_exercism',
        'category': 'api_misuse',
        'difficulty': 'medium',
        'lines_changed': 1,
        'description': 'map_applied discards map object, not converting to list',
        'buggy': 'def double_all(nums):\n    return map(lambda x: x * 2, nums)\n',
        'fixed': 'def double_all(nums):\n    return list(map(lambda x: x * 2, nums))\n',
        'test': 'from solution import double_all\n\n\ndef test_matches_reference():\n    cases = [[1, 2, 3], [], [-1, 0, 1], [10, 20, 30]]\n    for nums in cases:\n        out = double_all(nums)\n        assert out == [n * 2 for n in nums]\n        assert isinstance(out, list)\n\n',
    },
    {
        'task_id': 'task_078',
        'source': 'mutation_exercism',
        'category': 'api_misuse',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'enumerate_wrong_start starts enumeration at 0 instead of 1 for 1-indexed positions',
        'buggy': 'def rank_items(items):\n    return [(i, item) for i, item in enumerate(items)]\n',
        'fixed': 'def rank_items(items):\n    return [(i, item) for i, item in enumerate(items, 1)]\n',
        'test': 'from solution import rank_items\n\n\ndef test_starts_at_one():\n    cases = [["a", "b", "c"], [], ["x"], [1, 2, 3, 4]]\n    for items in cases:\n        out = rank_items(items)\n        assert out == list(enumerate(items, start=1))\n\n',
    },
    {
        'task_id': 'task_079',
        'source': 'mutation_exercism',
        'category': 'api_misuse',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'max_with_wrong_key finds max by string length instead of numeric value',
        'buggy': 'def find_longest(words):\n    return max(words, key=int)\n',
        'fixed': 'def find_longest(words):\n    return max(words, key=len)\n',
        'test': 'from solution import find_longest\n\n\ndef test_matches_max_by_len():\n    cases = [\n        ["short", "longer", "longest"],\n        ["a"],\n        ["ab", "cd"],\n        ["abc", "de", "fghij"],\n    ]\n    for words in cases:\n        assert find_longest(words) == max(words, key=len)\n\n',
    },
    {
        'task_id': 'task_080',
        'source': 'mutation_exercism',
        'category': 'api_misuse',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'filter_kept keeps matching elements correctly but returns filter object, not list',
        'buggy': 'def filter_positive(nums):\n    return filter(lambda x: x > 0, nums)\n',
        'fixed': 'def filter_positive(nums):\n    return list(filter(lambda x: x > 0, nums))\n',
        'test': 'from solution import filter_positive\n\n\ndef test_keeps_only_positive():\n    cases = [[1, -2, 3, -4, 5], [], [-1, -2], [1, 2, 3], [0, 1, -1]]\n    for nums in cases:\n        out = filter_positive(nums)\n        assert out == [n for n in nums if n > 0]\n        assert isinstance(out, list)\n\n',
    },
    {
        'task_id': 'task_081',
        'source': 'mutation_exercism',
        'category': 'boundary',
        'difficulty': 'easy',
        'lines_changed': 2,
        'description': "single_element_max returns float('-inf') for single-element list due to loop not executing",
        'buggy': "def find_max_loop(nums):\n    max_val = float('-inf')\n    for i in range(1, len(nums)):\n        if nums[i] > max_val:\n            max_val = nums[i]\n    return max_val\n",
        'fixed': 'def find_max_loop(nums):\n    max_val = nums[0]\n    for i in range(1, len(nums)):\n        if nums[i] > max_val:\n            max_val = nums[i]\n    return max_val\n',
        'test': 'from solution import find_max_loop\n\n\ndef test_matches_builtin_max():\n    cases = [[5], [3, 1, 4, 1, 5], [-1, -2, -3], [0, 0, 0], [10, -10]]\n    for nums in cases:\n        assert find_max_loop(nums) == max(nums)\n\n',
    },
    {
        'task_id': 'task_082',
        'source': 'mutation_exercism',
        'category': 'boundary',
        'difficulty': 'easy',
        'lines_changed': 2,
        'description': 'zero_power returns 0 for any base raised to power 0 due to wrong base case',
        'buggy': 'def power(base, exp):\n    if exp == 0:\n        return 0\n    return base * power(base, exp - 1)\n',
        'fixed': 'def power(base, exp):\n    if exp == 0:\n        return 1\n    return base * power(base, exp - 1)\n',
        'test': 'from solution import power\n\n\ndef test_matches_pow():\n    cases = [(5, 0), (5, 1), (3, 2), (0, 3), (1, 100), (2, 5), (7, 3)]\n    for b, e in cases:\n        assert power(b, e) == b ** e\n\n',
    },
    {
        'task_id': 'task_083',
        'source': 'mutation_exercism',
        'category': 'boundary',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'fibonacci_zero returns 1 for n=0 instead of 0',
        'buggy': 'def fib(n):\n    if n <= 1:\n        return 1\n    return fib(n - 1) + fib(n - 2)\n',
        'fixed': 'def fib(n):\n    if n == 0:\n        return 0\n    if n == 1:\n        return 1\n    return fib(n - 1) + fib(n - 2)\n',
        'test': 'from solution import fib\n\n\ndef _ref(n):\n    if n == 0:\n        return 0\n    if n == 1:\n        return 1\n    a, b = 0, 1\n    for _ in range(n - 1):\n        a, b = b, a + b\n    return b\n\n\ndef test_matches_reference():\n    for n in [0, 1, 2, 3, 5, 7, 10]:\n        assert fib(n) == _ref(n)\n\n',
    },
    {
        'task_id': 'task_084',
        'source': 'mutation_exercism',
        'category': 'boundary',
        'difficulty': 'easy',
        'lines_changed': 2,
        'description': 'single_char_palindrome returns False for single-character string',
        'buggy': 'def is_palindrome(s):\n    if len(s) < 2:\n        return False\n    return s == s[::-1]\n',
        'fixed': 'def is_palindrome(s):\n    return s == s[::-1]\n',
        'test': 'from solution import is_palindrome\n\n\ndef test_matches_reverse_check():\n    cases = ["a", "ab", "aa", "aba", "abc", "racecar", "", "abba"]\n    for s in cases:\n        assert is_palindrome(s) is (s == s[::-1])\n\n',
    },
    {
        'task_id': 'task_085',
        'source': 'mutation_exercism',
        'category': 'boundary',
        'difficulty': 'easy',
        'lines_changed': 2,
        'description': "empty_string_split returns [''] instead of [] for empty string",
        'buggy': "def get_words(sentence):\n    return sentence.split(' ')\n",
        'fixed': 'def get_words(sentence):\n    return sentence.split()\n',
        'test': 'from solution import get_words\n\n\ndef test_matches_split():\n    cases = ["hello world", "  spaced  out  ", "single", "", "a b c d"]\n    for s in cases:\n        assert get_words(s) == s.split()\n\n',
    },
    {
        'task_id': 'task_086',
        'source': 'mutation_exercism',
        'category': 'boundary',
        'difficulty': 'easy',
        'lines_changed': 2,
        'description': 'matrix_1x1_trace returns empty list instead of [element] for 1x1 matrix',
        'buggy': 'def get_diagonal(matrix):\n    n = len(matrix)\n    return [matrix[i][i] for i in range(1, n)]\n',
        'fixed': 'def get_diagonal(matrix):\n    n = len(matrix)\n    return [matrix[i][i] for i in range(n)]\n',
        'test': 'from solution import get_diagonal\n\n\ndef _ref(m):\n    return [m[i][i] for i in range(len(m))]\n\n\ndef test_matches_reference():\n    cases = [\n        [[1]],\n        [[1, 2], [3, 4]],\n        [[1, 0, 0], [0, 5, 0], [0, 0, 9]],\n    ]\n    for m in cases:\n        assert get_diagonal(m) == _ref(m)\n\n',
    },
    {
        'task_id': 'task_087',
        'source': 'mutation_exercism',
        'category': 'boundary',
        'difficulty': 'medium',
        'lines_changed': 2,
        'description': 'already_sorted_quicksort picks first element as pivot causing O(n^2) and wrong boundary handling',
        'buggy': 'def quicksort(arr):\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[0]\n    left = [x for x in arr[1:] if x < pivot]\n    right = [x for x in arr[1:] if x > pivot]\n    return quicksort(left) + [pivot] + quicksort(right)\n',
        'fixed': 'def quicksort(arr):\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[len(arr) // 2]\n    left = [x for x in arr if x < pivot]\n    middle = [x for x in arr if x == pivot]\n    right = [x for x in arr if x > pivot]\n    return quicksort(left) + middle + quicksort(right)\n',
        'test': 'import random\nfrom solution import quicksort\n\n\ndef test_sorts_correctly():\n    random.seed(3)\n    for _ in range(15):\n        arr = [random.randint(-20, 20) for _ in range(random.randint(0, 12))]\n        out = quicksort(list(arr))\n        assert out == sorted(arr)\n\n\ndef test_preserves_duplicates():\n    cases = [[3, 3, 3], [1, 1, 2, 2, 1], [5, 5, 5, 5, 5]]\n    for arr in cases:\n        out = quicksort(list(arr))\n        assert sorted(out) == sorted(arr)\n        assert len(out) == len(arr)\n\n',
    },
    {
        'task_id': 'task_088',
        'source': 'mutation_exercism',
        'category': 'boundary',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'modulo_by_zero returns 0 instead of raising when divisor is 0 in safe_mod',
        'buggy': 'def safe_mod(a, b):\n    if b == 0:\n        return 0\n    return a % b\n',
        'fixed': 'def safe_mod(a, b):\n    if b == 0:\n        return None\n    return a % b\n',
        'test': 'from solution import safe_mod\n\n\ndef test_matches_modulo():\n    cases = [(10, 3), (15, 4), (7, 7), (-5, 3), (0, 5)]\n    for a, b in cases:\n        assert safe_mod(a, b) == a % b\n\n\ndef test_zero_divisor_returns_none():\n    for a in [10, 0, -5]:\n        assert safe_mod(a, 0) is None\n\n',
    },
    {
        'task_id': 'task_089',
        'source': 'mutation_exercism',
        'category': 'boundary',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'string_repeat returns empty string for n=0 instead of empty string (wrong initial value)',
        'buggy': 'def repeat_string(s, n):\n    result = s\n    for _ in range(n - 1):\n        result += s\n    return result\n',
        'fixed': "def repeat_string(s, n):\n    result = ''\n    for _ in range(n):\n        result += s\n    return result\n",
        'test': 'from solution import repeat_string\n\n\ndef test_matches_string_mult():\n    cases = [("ab", 3), ("x", 5), ("hello", 2), ("a", 1), ("xyz", 0)]\n    for s, n in cases:\n        assert repeat_string(s, n) == s * n\n\n',
    },
    {
        'task_id': 'task_090',
        'source': 'mutation_exercism',
        'category': 'boundary',
        'difficulty': 'easy',
        'lines_changed': 1,
        'description': 'string_title uses wrong method: upper() instead of title() capitalizing everything',
        'buggy': 'def title_case(s):\n    return s.upper()\n',
        'fixed': 'def title_case(s):\n    return s.title()\n',
        'test': 'from solution import title_case\n\n\ndef test_matches_str_title():\n    cases = ["hello world", "the QUICK brown fox", "PYTHON", "a", "", "multiple   spaces"]\n    for s in cases:\n        assert title_case(s) == s.title()\n\n',
    },
]


def build_benchmark(output_dir: Path, validate: bool = False) -> list[tuple[str, str]]:
    """Generate task directories and optionally validate every generated task."""
    tasks_dir = output_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)

    print(f"Building {len(TASKS)} tasks in {tasks_dir}")
    failed_validation: list[tuple[str, str]] = []

    for task in TASKS:
        tid = str(task["task_id"])
        task_dir = tasks_dir / tid
        task_dir.mkdir(parents=True, exist_ok=True)

        (task_dir / "buggy.py").write_text(_normalize(task["buggy"]), encoding="utf-8")
        (task_dir / "fixed.py").write_text(_normalize(task["fixed"]), encoding="utf-8")
        (task_dir / "test_suite.py").write_text(_normalize(task["test"]), encoding="utf-8")

        metadata = {
            "task_id": tid,
            "source": task["source"],
            "category": task["category"],
            "difficulty": task["difficulty"],
            "lines_changed": task["lines_changed"],
            "description": task["description"],
        }
        (task_dir / "metadata.json").write_text(
            json.dumps(metadata, indent=2),
            encoding="utf-8",
        )

        if validate:
            ok, msg = validate_task(task_dir)
            status = "OK" if ok else "FAIL"
            print(f"  [{status}] {tid}: {msg}")
            if not ok:
                failed_validation.append((tid, msg))

    print(f"\nGenerated {len(TASKS)} tasks.")
    _print_validation_summary(failed_validation, validate)
    return failed_validation


def validate_task(task_dir: Path) -> tuple[bool, str]:
    """Return true iff buggy.py fails at least one test and fixed.py passes all tests."""
    buggy = (task_dir / "buggy.py").read_text(encoding="utf-8")
    fixed = (task_dir / "fixed.py").read_text(encoding="utf-8")

    buggy_passes = _run_tests(task_dir, buggy)
    if buggy_passes is None:
        return False, "timeout on buggy"
    fixed_passes = _run_tests(task_dir, fixed)
    if fixed_passes is None:
        return False, "timeout on fixed"

    if not buggy_passes and fixed_passes:
        return True, "buggy fails, fixed passes"
    if buggy_passes and fixed_passes:
        return False, "buggy also passes (bug not detectable by tests)"
    if not buggy_passes and not fixed_passes:
        return False, "fixed does not pass tests"
    return False, "unexpected validation state"


def validate_only(output_dir: Path) -> list[tuple[str, str]]:
    """Validate existing task directories without rebuilding them."""
    tasks_dir = output_dir / "tasks"
    task_dirs = sorted(path for path in tasks_dir.glob("task_*") if path.is_dir())
    failed: list[tuple[str, str]] = []

    print(f"Validating {len(task_dirs)} existing tasks in {tasks_dir}")
    for task_dir in task_dirs:
        ok, msg = validate_task(task_dir)
        status = "OK" if ok else "FAIL"
        print(f"  [{status}] {task_dir.name}: {msg}")
        if not ok:
            failed.append((task_dir.name, msg))

    print(f"\nValidated {len(task_dirs)} tasks.")
    _print_validation_summary(failed, validate=True)
    return failed


def _run_tests(task_dir: Path, solution_code: str, timeout_s: int = 15) -> bool | None:
    """Return True if tests pass, False if tests fail, None on timeout."""
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        shutil.copy(task_dir / "test_suite.py", tmpdir / "test_suite.py")
        (tmpdir / "solution.py").write_text(solution_code, encoding="utf-8")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "test_suite.py", "-q", "--tb=no", "--no-header"],
                cwd=tmpdir,
                capture_output=True,
                timeout=timeout_s,
                text=True,
            )
        except subprocess.TimeoutExpired:
            return None
    return result.returncode == 0


def _normalize(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"


def _print_validation_summary(failed: list[tuple[str, str]], validate: bool) -> None:
    if not validate:
        return
    if failed:
        print(f"\n{len(failed)} tasks failed validation:")
        for tid, msg in failed:
            print(f"  {tid}: {msg}")
    else:
        print("All tasks validated successfully.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true", help="Build then validate all tasks")
    parser.add_argument("--validate-only", action="store_true", help="Validate existing tasks without rebuilding")
    parser.add_argument("--output", default=str(Path(__file__).parent), help="Output directory")
    args = parser.parse_args()

    output_dir = Path(args.output)
    failed = validate_only(output_dir) if args.validate_only else build_benchmark(output_dir, args.validate)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
