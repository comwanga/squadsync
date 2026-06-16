from collections import Counter
from app.services.allocation_engine import score_teams, _tiebreak


def test_tiebreak_seed_zero_is_plain_id():
    assert _tiebreak("abc", 0) == "abc"


def test_tiebreak_nonzero_seed_actually_varies():
    # Guards against a regression where the seed is ignored.
    assert _tiebreak("abc", 7) != "abc"
    assert _tiebreak("abc", 7) != _tiebreak("abc", 8)


def test_even_teams_high_skill():
    skill, role, fair = score_teams([3.0, 3.0, 3.0], [Counter(), Counter(), Counter()], {})
    assert skill == 100.0
    assert role == 100.0
    assert fair == 100.0


def test_lopsided_teams_lower_skill():
    skill, _, _ = score_teams([6.0, 1.0], [Counter(), Counter()], {})
    assert 0.0 <= skill < 100.0


def test_role_balance_partial_fulfillment():
    counts = [Counter({"technical": 1}), Counter()]
    _, role, _ = score_teams([2.0, 2.0], counts, {"technical": 1})
    assert role == 50.0


def test_role_balance_full():
    counts = [Counter({"technical": 1}), Counter({"technical": 1})]
    _, role, _ = score_teams([2.0, 2.0], counts, {"technical": 1})
    assert role == 100.0
