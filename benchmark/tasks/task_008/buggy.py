def count_pairs_with_sum(arr, target):
    count = 0
    n = len(arr)
    for i in range(n):
        for j in range(i + 1, n):
            if arr[i] + arr[j] == target * 2:
                count += 1
    return count
