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

# Cap participants per AI call so a batch's tool-use output cannot exceed
# _MAX_TOKENS and truncate — a truncated tool call would fail to parse and
# silently drop the whole batch to the deterministic fallback.
_BATCH_SIZE = 25
_MAX_TOKENS = 4096

_SYSTEM_INSTRUCTIONS = (
    "You normalize each participant's free-text strength into exactly one of a "
    "fixed set of categories so a downstream deterministic engine can compare "
    "them. You never assign teams. Map each participant to the single best-fit "
    "category. If a participant's text is too vague, empty, or unrelated to every "
    "category, OMIT them from the assignments instead of guessing — an omitted "
    "participant is handled by a deterministic fallback and an organizer can set "
    "their category by hand."
)


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", text.strip().lower()).strip("_")
    return s or "other"


def _category_catalog() -> str:
    return ", ".join(f"{v} ({STRENGTH_LABELS[v]})" for v in CONCRETE_STRENGTHS)


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


def _build_request(event: Event, participants: list[Participant]) -> dict:
    """Build the Messages API kwargs. Pure (no network) so it is unit-testable.

    The static instructions + category catalog go in a cacheable system block;
    the per-event context and participant list go in the user message.
    """
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
    return {
        "model": settings.CATEGORIZATION_MODEL,
        "max_tokens": _MAX_TOKENS,
        "system": [{
            "type": "text",
            "text": f"{_SYSTEM_INSTRUCTIONS}\n\nAvailable categories: {_category_catalog()}",
            "cache_control": {"type": "ephemeral"},
        }],
        "tools": [tool],
        "tool_choice": {"type": "tool", "name": "assign_categories"},
        "messages": [{
            "role": "user",
            "content": (
                f"Event: {event.title}\nDescription: {event.description or '(none)'}\n\n"
                f"Map each participant's free-text strength to the best category, "
                f"omitting any that are too unclear to place.\n{people}"
            ),
        }],
    }


def _parse_assignments(content_blocks) -> dict[str, str]:
    """Extract {id: category} from tool_use blocks, dropping out-of-taxonomy values."""
    out: dict[str, str] = {}
    for block in content_blocks:
        if getattr(block, "type", None) == "tool_use":
            for a in block.input.get("assignments", []):
                if a.get("category") in CONCRETE_STRENGTHS and a.get("id"):
                    out[a["id"]] = a["category"]
    return out


def _classify(event: Event, participants: list[Participant]) -> dict[str, str]:
    """Call Claude for one batch; return {participant_id: concrete_category}. Raises on failure."""
    import anthropic

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    msg = client.messages.create(**_build_request(event, participants))
    return _parse_assignments(msg.content)


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
        # Batch so output can't truncate, and so one failing batch only forces its
        # own members to the fallback rather than dumping everyone.
        for i in range(0, len(pending), _BATCH_SIZE):
            batch = pending[i:i + _BATCH_SIZE]
            try:
                mapping.update(_classify(event, batch))
            except Exception as exc:  # noqa: BLE001 — AI is best-effort, per batch
                logger.warning("Categorization AI batch failed, using fallback: %s", exc)

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
