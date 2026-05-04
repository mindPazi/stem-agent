def longest_common_prefix(strs):
    if not strs:
        return ''
    prefix = strs[0]
    for s in strs[1:]:
        while not prefix.startswith(s[:len(prefix)]):
            prefix = prefix[:-1]
            if not prefix:
                return ''
    return prefix
