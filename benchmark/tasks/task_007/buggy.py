def max_sliding_window(nums, k):
    result = []
    for i in range(len(nums) - k + 1):
        result.append(max(nums[i:i + k + 1]))
    return result
