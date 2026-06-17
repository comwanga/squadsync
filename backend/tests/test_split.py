import pytest
from app.services.payout_service import compute_split


def test_even_split_no_remainder():
    # 300 sats over 3 members -> 100 each, order preserved
    assert compute_split(["a", "b", "c"], 300) == [("a", 100), ("b", 100), ("c", 100)]


def test_remainder_goes_to_earliest_members():
    # 100 sats over 3 -> 34, 33, 33 (remainder 1 to the first member)
    assert compute_split(["a", "b", "c"], 100) == [("a", 34), ("b", 33), ("c", 33)]


def test_single_member_gets_everything():
    assert compute_split(["a"], 210) == [("a", 210)]


def test_zero_members_raises():
    with pytest.raises(ValueError):
        compute_split([], 100)


def test_total_below_member_count_raises():
    # cannot give every member at least 1 sat
    with pytest.raises(ValueError):
        compute_split(["a", "b", "c"], 2)
