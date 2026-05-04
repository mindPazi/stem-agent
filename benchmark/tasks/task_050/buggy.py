def find_min(nums):
    min_val = 0
    for num in nums:
        if num < min_val:
            min_val = num
    return min_val
