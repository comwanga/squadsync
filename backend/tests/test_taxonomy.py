from app.core.taxonomy import (
    PRIMARY_STRENGTHS, CONCRETE_STRENGTHS, EXPERIENCE_LEVELS, EXPERIENCE_SCORE,
)


def test_strength_values():
    assert "other" in PRIMARY_STRENGTHS
    assert "technical" in PRIMARY_STRENGTHS
    assert len(PRIMARY_STRENGTHS) == 8


def test_concrete_excludes_other():
    assert "other" not in CONCRETE_STRENGTHS
    assert set(CONCRETE_STRENGTHS) == set(PRIMARY_STRENGTHS) - {"other"}


def test_experience_scale():
    assert EXPERIENCE_LEVELS == ("beginner", "intermediate", "advanced")
    assert EXPERIENCE_SCORE == {"beginner": 1.0, "intermediate": 2.0, "advanced": 3.0}
