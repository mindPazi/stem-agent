def majority_element(nums):
    n = len(nums)
    counts = {}
    for num in nums:
        counts[num] = counts.get(num, 0) + 1
        if counts[num] > n // 2:
            return num
    return -1
