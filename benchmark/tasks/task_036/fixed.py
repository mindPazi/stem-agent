def max_in_matrix(matrix):
    if not matrix or not matrix[0]:
        return None
    return max(max(row) for row in matrix)
