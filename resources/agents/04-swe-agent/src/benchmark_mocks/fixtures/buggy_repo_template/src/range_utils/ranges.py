def ranges_overlap(left: tuple[int, int], right: tuple[int, int]) -> bool:
    """Return whether two half-open integer ranges overlap.

    Ranges use Python's half-open convention: (start, end) contains values
    start <= value < end. Empty ranges such as (2, 2) never overlap anything.
    """
    left_start, left_end = left
    right_start, right_end = right
    return left_start <= right_end and right_start <= left_end
