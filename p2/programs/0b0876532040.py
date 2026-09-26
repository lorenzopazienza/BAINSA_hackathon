def construct(d):
    """Binary reflected Gray code order: label k -> vertex k ^ (k >> 1)."""
    n = 1 << d
    return [k ^ (k >> 1) for k in range(n)]
