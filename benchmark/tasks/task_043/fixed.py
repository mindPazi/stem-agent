def max_subarray(nums):
    max_sum = current = nums[0]
    for num in nums[1:]:
        current = max(current + num, num)
        max_sum = max(max_sum, current)
    return max_sum
