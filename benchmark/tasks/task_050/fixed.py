def find_min(nums):
    min_val = nums[0]
    for num in nums[1:]:
        if num < min_val:
            min_val = num
    return min_val
