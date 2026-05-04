def find_max_loop(nums):
    max_val = float('-inf')
    for i in range(1, len(nums)):
        if nums[i] > max_val:
            max_val = nums[i]
    return max_val
