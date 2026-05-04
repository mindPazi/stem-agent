def diagonal_sum(matrix):
    n = len(matrix)
    total = 0
    for i in range(n + 1):
        total += matrix[i][i]
    return total
