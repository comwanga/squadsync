"""Single source of truth for the universal participant taxonomy.

Used by the registration schema, the AI normalization prompt, and the
allocation engine so the category set never drifts across layers.
"""

# Universal "Primary Strength" values the registrant can choose.
PRIMARY_STRENGTHS: tuple[str, ...] = (
    "technical",
    "design",
    "planning",
    "coordination",
    "communication",
    "research",
    "domain_expert",
    "other",
)

# Human-readable labels (frontend mirrors these; kept here for prompts/exports).
STRENGTH_LABELS: dict[str, str] = {
    "technical": "Technical / Hands-on",
    "design": "Design / Creative",
    "planning": "Planning / Strategy",
    "coordination": "Coordination / Operations",
    "communication": "Communication / Outreach",
    "research": "Research / Analysis",
    "domain_expert": "Domain Expert",
    "other": "Other",
}

# The concrete categories the AI must map an "Other" entry into (excludes "other").
CONCRETE_STRENGTHS: tuple[str, ...] = tuple(s for s in PRIMARY_STRENGTHS if s != "other")

EXPERIENCE_LEVELS: tuple[str, ...] = ("beginner", "intermediate", "advanced")
EXPERIENCE_SCORE: dict[str, float] = {"beginner": 1.0, "intermediate": 2.0, "advanced": 3.0}
