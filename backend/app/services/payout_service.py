"""Lightning payout: deterministic split + orchestration.

`compute_split` is pure and reproducible: an integer even split with the
remainder assigned to the earliest members (by the order they are passed in).
The orchestration functions are added in a later task.
"""
from typing import Sequence, TypeVar

T = TypeVar("T")


def compute_split(recipients: Sequence[T], total_sats: int) -> list[tuple[T, int]]:
    """Split `total_sats` evenly across `recipients`, remainder to the first members.

    Raises ValueError if there are no recipients or fewer sats than recipients
    (every member must receive at least 1 sat).
    """
    n = len(recipients)
    if n == 0:
        raise ValueError("no recipients")
    if total_sats < n:
        raise ValueError("total_sats must be at least one sat per recipient")
    base, remainder = divmod(total_sats, n)
    return [(r, base + (1 if i < remainder else 0)) for i, r in enumerate(recipients)]
