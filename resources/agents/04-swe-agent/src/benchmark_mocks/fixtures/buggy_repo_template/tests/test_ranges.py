from range_utils import ranges_overlap


def test_overlapping_ranges():
    assert ranges_overlap((1, 5), (4, 8)) is True


def test_touching_half_open_ranges_do_not_overlap():
    assert ranges_overlap((1, 5), (5, 8)) is False


def test_empty_range_does_not_overlap():
    assert ranges_overlap((2, 2), (1, 3)) is False


def test_disjoint_ranges():
    assert ranges_overlap((10, 12), (1, 3)) is False
