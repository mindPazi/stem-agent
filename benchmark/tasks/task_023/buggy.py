def transpose(matrix):
    n = len(matrix)
    for i in range(n):
        for j in range(i + 1, n):
            matrix[i][j], matrix[i][j] = matrix[j][i], matrix[i][j]
    return matrix
