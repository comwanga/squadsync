from app.services.allocation_engine import compute_composite_score


def test_beginner():
    assert compute_composite_score("beginner") == 1.0


def test_intermediate():
    assert compute_composite_score("intermediate") == 2.0


def test_advanced():
    assert compute_composite_score("advanced") == 3.0
