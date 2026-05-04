"""Fix the 12 tasks where the bug is not detectable by tests."""
from __future__ import annotations
import json
from pathlib import Path

TASKS_DIR = Path(__file__).parent / "tasks"


def write_task(tid: str, buggy: str, fixed: str, test: str, desc: str) -> None:
    d = TASKS_DIR / tid
    (d / "buggy.py").write_text(buggy.strip() + "\n", encoding="utf-8")
    (d / "fixed.py").write_text(fixed.strip() + "\n", encoding="utf-8")
    (d / "test_suite.py").write_text(test.strip() + "\n", encoding="utf-8")
    meta = json.loads((d / "metadata.json").read_text(encoding="utf-8"))
    meta["description"] = desc
    (d / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"  Fixed {tid}")


# task_004: count_substrings - range(n) misses last valid start index
write_task(
    "task_004",
    buggy="""
def count_substrings(s, sub):
    count = 0
    for i in range(len(s) - len(sub)):
        if s[i:i + len(sub)] == sub:
            count += 1
    return count
""",
    fixed="""
def count_substrings(s, sub):
    count = 0
    for i in range(len(s) - len(sub) + 1):
        if s[i:i + len(sub)] == sub:
            count += 1
    return count
""",
    test="""
from solution import count_substrings

def test_full_match():
    assert count_substrings("abc", "abc") == 1

def test_basic():
    assert count_substrings("hello", "l") == 2

def test_none():
    assert count_substrings("hello", "z") == 0

def test_last_position():
    assert count_substrings("abab", "ab") == 2
""",
    desc="count_substrings uses range(n - len(sub)) missing the last valid start position",
)

# task_005: remove_duplicates - appends when equal instead of when different
write_task(
    "task_005",
    buggy="""
def remove_duplicates(arr):
    if not arr:
        return []
    result = []
    for i in range(len(arr) - 1):
        if arr[i] == arr[i + 1]:
            result.append(arr[i])
    result.append(arr[-1])
    return result
""",
    fixed="""
def remove_duplicates(arr):
    if not arr:
        return []
    result = []
    for i in range(len(arr) - 1):
        if arr[i] != arr[i + 1]:
            result.append(arr[i])
    result.append(arr[-1])
    return result
""",
    test="""
from solution import remove_duplicates

def test_no_dups():
    assert remove_duplicates([1, 2, 3]) == [1, 2, 3]

def test_all_same():
    assert remove_duplicates([5, 5, 5]) == [5]

def test_empty():
    assert remove_duplicates([]) == []

def test_single():
    assert remove_duplicates([7]) == [7]

def test_trailing():
    assert remove_duplicates([1, 2, 2]) == [1, 2]
""",
    desc="remove_duplicates appends when arr[i] == arr[i+1] (inverted condition)",
)

# task_008: count_pairs - checks target*2 instead of target
write_task(
    "task_008",
    buggy="""
def count_pairs_with_sum(arr, target):
    count = 0
    n = len(arr)
    for i in range(n):
        for j in range(i + 1, n):
            if arr[i] + arr[j] == target * 2:
                count += 1
    return count
""",
    fixed="""
def count_pairs_with_sum(arr, target):
    count = 0
    n = len(arr)
    for i in range(n):
        for j in range(i + 1, n):
            if arr[i] + arr[j] == target:
                count += 1
    return count
""",
    test="""
from solution import count_pairs_with_sum

def test_basic():
    assert count_pairs_with_sum([1, 5, 7, -1, 5], 6) == 3

def test_none():
    assert count_pairs_with_sum([1, 2, 3], 10) == 0

def test_one():
    assert count_pairs_with_sum([1, 9], 10) == 1
""",
    desc="count_pairs_with_sum checks arr[i]+arr[j] == target*2 instead of target",
)

# task_011: run_length_encode - initializes count to 2 instead of 1
write_task(
    "task_011",
    buggy="""
def run_length_encode(s):
    if not s:
        return ''
    result = []
    count = 2
    for i in range(1, len(s)):
        if s[i] == s[i - 1]:
            count += 1
        else:
            result.append(f'{count}{s[i-1]}')
            count = 2
    result.append(f'{count}{s[-1]}')
    return ''.join(result)
""",
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
""",
    test="""
from solution import run_length_encode

def test_single():
    assert run_length_encode("a") == "1a"

def test_no_repeat():
    assert run_length_encode("abc") == "1a1b1c"

def test_basic():
    assert run_length_encode("aabbbcc") == "2a3b2c"

def test_all_same():
    assert run_length_encode("aaaa") == "4a"

def test_empty():
    assert run_length_encode("") == ""
""",
    desc="run_length_encode initializes count to 2 instead of 1, inflating all counts by 1",
)

# task_012: next_greater_element - uses >= instead of >, returning element itself for equal
write_task(
    "task_012",
    buggy="""
def next_greater_element(arr):
    n = len(arr)
    result = [-1] * n
    for i in range(n):
        for j in range(i + 1, n):
            if arr[j] >= arr[i]:
                result[i] = arr[j]
                break
    return result
""",
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
""",
    test="""
from solution import next_greater_element

def test_equal_elements():
    assert next_greater_element([3, 3, 5]) == [5, 5, -1]

def test_basic():
    assert next_greater_element([4, 5, 2, 10]) == [5, 10, 10, -1]

def test_descending():
    assert next_greater_element([5, 4, 3]) == [-1, -1, -1]

def test_single():
    assert next_greater_element([1]) == [-1]
""",
    desc="next_greater_element uses >= instead of >, incorrectly returning equal elements",
)

# task_015: trap_rain_water - uses max instead of min for water level
write_task(
    "task_015",
    buggy="""
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
        water += max(left_max[i], right_max[i]) - height[i]
    return water
""",
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
""",
    test="""
from solution import trap_rain_water

def test_basic():
    assert trap_rain_water([0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1]) == 6

def test_two_walls():
    assert trap_rain_water([3, 0, 3]) == 3

def test_no_water():
    assert trap_rain_water([3, 2, 1]) == 0

def test_short():
    assert trap_rain_water([1, 2]) == 0
""",
    desc="trap_rain_water uses max(left_max, right_max) instead of min, computing wrong water level",
)

# task_021: is_anagram - wrong early return (True instead of False for different lengths)
write_task(
    "task_021",
    buggy="""
def is_anagram(s, t):
    if len(s) != len(t):
        return True
    counts = {}
    for ch in s:
        counts[ch] = counts.get(ch, 0) + 1
    for ch in t:
        counts[ch] = counts.get(ch, 0) - 1
    return all(v == 0 for v in counts.values())
""",
    fixed="""
def is_anagram(s, t):
    if len(s) != len(t):
        return False
    counts = {}
    for ch in s:
        counts[ch] = counts.get(ch, 0) + 1
    for ch in t:
        counts[ch] = counts.get(ch, 0) - 1
    return all(v == 0 for v in counts.values())
""",
    test="""
from solution import is_anagram

def test_different_lengths():
    assert is_anagram("a", "ab") is False

def test_anagram():
    assert is_anagram("anagram", "nagaram") is True

def test_not_anagram():
    assert is_anagram("rat", "car") is False

def test_same():
    assert is_anagram("a", "a") is True
""",
    desc="is_anagram returns True instead of False when lengths differ",
)

# task_027: longest_common_prefix - fails when second string is shorter than prefix
write_task(
    "task_027",
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
""",
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
""",
    test="""
from solution import longest_common_prefix

def test_shorter_string():
    assert longest_common_prefix(["ba", "b"]) == "b"

def test_basic():
    assert longest_common_prefix(["flower", "flow", "flight"]) == "fl"

def test_none():
    assert longest_common_prefix(["dog", "racecar", "car"]) == ""

def test_one():
    assert longest_common_prefix(["alone"]) == "alone"
""",
    desc="longest_common_prefix checks prefix.startswith(s) instead of s.startswith(prefix)",
)

# task_042: parse_int - returns absolute value, hiding negative numbers
write_task(
    "task_042",
    buggy="""
def parse_int(s):
    return abs(int(s.strip()))
""",
    fixed="""
def parse_int(s):
    return int(s.strip())
""",
    test="""
from solution import parse_int

def test_positive():
    assert parse_int("42") == 42

def test_negative():
    assert parse_int("-5") == -5

def test_spaces():
    assert parse_int("  10  ") == 10

def test_zero():
    assert parse_int("0") == 0
""",
    desc="parse_int wraps result in abs(), turning negative numbers positive",
)

# task_055: gcd_recursive - uses a//b instead of a%b
write_task(
    "task_055",
    buggy="""
def gcd_recursive(a, b):
    if b == 0:
        return a
    return gcd_recursive(b, a // b)
""",
    fixed="""
def gcd_recursive(a, b):
    if b == 0:
        return a
    return gcd_recursive(b, a % b)
""",
    test="""
from solution import gcd_recursive

def test_basic():
    assert gcd_recursive(48, 18) == 6

def test_coprime():
    assert gcd_recursive(7, 13) == 1

def test_same():
    assert gcd_recursive(5, 5) == 5

def test_multiples():
    assert gcd_recursive(100, 25) == 25
""",
    desc="gcd_recursive uses integer division (a//b) instead of modulo (a%b)",
)

# task_057: two_sum_exists - adds complement to seen instead of num
write_task(
    "task_057",
    buggy="""
def two_sum_exists(nums, target):
    seen = set()
    for num in nums:
        if target - num in seen:
            return True
        seen.add(target - num)
    return False
""",
    fixed="""
def two_sum_exists(nums, target):
    seen = set()
    for num in nums:
        if target - num in seen:
            return True
        seen.add(num)
    return False
""",
    test="""
from solution import two_sum_exists

def test_found():
    assert two_sum_exists([2, 7, 11, 15], 9) is True

def test_not_found():
    assert two_sum_exists([1, 2, 3], 10) is False

def test_two_elements():
    assert two_sum_exists([3, 7], 10) is True

def test_negative():
    assert two_sum_exists([-1, 4, 5], 3) is True
""",
    desc="two_sum_exists adds complement to seen set instead of num, breaking lookup",
)

# task_058: flatten - uses += [item] (nesting) instead of .extend()
write_task(
    "task_058",
    buggy="""
def flatten(lst):
    result = []
    for item in lst:
        if isinstance(item, list):
            result += [flatten(item)]
        else:
            result.append(item)
    return result
""",
    fixed="""
def flatten(lst):
    result = []
    for item in lst:
        if isinstance(item, list):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result
""",
    test="""
from solution import flatten

def test_basic():
    assert flatten([1, [2, 3], [4, [5]]]) == [1, 2, 3, 4, 5]

def test_flat():
    assert flatten([1, 2, 3]) == [1, 2, 3]

def test_empty():
    assert flatten([]) == []

def test_deep():
    assert flatten([[[1]], [2]]) == [1, 2]
""",
    desc="flatten uses += [sublist] creating nested results instead of result.extend()",
)

print("All fixes applied.")
