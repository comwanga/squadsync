"""Normalize free-text 'Other' strengths into universal categories.

Claude (Haiku) only interprets meaning; it never assigns teams. When no API key
is configured or the call fails, each Other entry becomes its own slug bucket so
allocation still works deterministically.
"""
import logging
import re
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.taxonomy import CONCRETE_STRENGTHS, STRENGTH_LABELS
from app.models.event import Event
from app.models.participant import Participant

logger = logging.getLogger(__name__)


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", text.strip().lower()).strip("_")
    return s or "other"


def _pending(db: Session, event_id: UUID) -> list[Participant]:
    return (
        db.query(Participant)
        .filter(
            Participant.event_id == event_id,
            Participant.primary_strength == "other",
            Participant.strength_source != "manual",
            Participant.normalized_strength.is_(None),
        )
        .all()
    )


def _classify(event: Event, participants: list[Participant]) -> dict[str, str]:
    """Call Claude; return {participant_id: concrete_category}. Raises on failure."""
    import anthropic

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    categories = ", ".join(f"{v} ({STRENGTH_LABELS[v]})" for v in CONCRETE_STRENGTHS)
    people = "\n".join(f"- id={p.id}: {p.strength_other}" for p in participants)
    tool = {
        "name": "assign_categories",
        "description": "Assign each participant to the single best-fit category.",
        "input_schema": {
            "type": "object",
            "properties": {
                "assignments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "category": {"type": "string", "enum": list(CONCRETE_STRENGTHS)},
                        },
                        "required": ["id", "category"],
                    },
                }
            },
            "required": ["assignments"],
        },
    }
    msg = client.messages.create(
        model=settings.CATEGORIZATION_MODEL,
        max_tokens=1024,
        tools=[tool],
        tool_choice={"type": "tool", "name": "assign_categories"},
        messages=[{
            "role": "user",
            "content": (
                f"Event: {event.title}\nDescription: {event.description or '(none)'}\n\n"
                f"Available categories: {categories}\n\n"
                f"Map each participant's free-text strength to the best category.\n{people}"
            ),
        }],
    )
    out: dict[str, str] = {}
    for block in msg.content:
        if getattr(block, "type", None) == "tool_use":
            for a in block.input["assignments"]:
                if a["category"] in CONCRETE_STRENGTHS:
                    out[a["id"]] = a["category"]
    return out


def normalize_pending(db: Session, event_id: UUID) -> dict[str, int]:
    """Fill normalized_strength for un-normalized Other entries. Never raises.

    Returns counts of how many entries were set via AI vs deterministic fallback
    in this call.
    """
    counts = {"ai": 0, "fallback": 0}
    pending = _pending(db, event_id)
    if not pending:
        return counts
    event = db.query(Event).filter(Event.id == event_id).first()

    mapping: dict[str, str] = {}
    if settings.ANTHROPIC_API_KEY:
        try:
            mapping = _classify(event, pending)
        except Exception as exc:  # noqa: BLE001 — AI is best-effort
            logger.warning("Categorization AI failed, using fallback: %s", exc)
            mapping = {}

    for p in pending:
        ai_cat = mapping.get(str(p.id))
        if ai_cat:
            p.normalized_strength = ai_cat
            p.strength_source = "ai"
            counts["ai"] += 1
        else:
            p.normalized_strength = _slug(p.strength_other or "other")
            p.strength_source = "fallback"
            counts["fallback"] += 1
    db.commit()
    return counts
