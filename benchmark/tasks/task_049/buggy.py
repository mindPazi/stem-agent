def find_max(nums):
    max_val = 0
    for num in nums:
        if num > max_val:
            max_val = num
    return max_val
