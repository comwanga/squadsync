"""Generate a short, PII-free "why this team works" rationale per team.

Descriptive only — never reads into or changes the deterministic allocation
engine. Mirrors categorization_service: pure _build_request/_parse helpers plus a
monkeypatchable _classify. The AI input carries no participant names or emails.
"""
import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.allocation import Allocation
from app.models.event import Event
from app.models.participant import Participant
from app.models.team import Team, TeamMember

logger = logging.getLogger(__name__)

_MAX_TOKENS = 4096

_SYSTEM_INSTRUCTIONS = (
    "You explain why each already-formed team is balanced. You do NOT form or change "
    "teams — you describe what exists. For each team return a short title (<=5 words), a "
    "one-sentence summary, a list of strengths, and a list of coverage gaps, grounded in "
    "the members' roles and experience. Never name or invent individuals; describe the "
    "composition only. If a team is too sparse to assess, omit it from the response."
)


class RationaleUnavailable(Exception):
    """Raised when AI rationale cannot run (no ANTHROPIC_API_KEY configured)."""


def _team_payloads(db: Session, allocation: Allocation) -> list[dict]:
    """PII-free composition per team: roles, experience, and any tech_stack/interests."""
    payloads: list[dict] = []
    teams = db.query(Team).filter(Team.allocation_id == allocation.id).all()
    for team in teams:
        members = (
            db.query(Participant)
            .join(TeamMember, Participant.id == TeamMember.participant_id)
            .filter(TeamMember.team_id == team.id)
            .all()
        )
        payloads.append({
            "id": str(team.id),
            "name": team.name,
            "members": [{
                "role": m.normalized_strength or m.primary_strength,
                "experience": m.experience_level,
                "tech_stack": m.tech_stack or [],
                "interests": m.interests or [],
            } for m in members],
        })
    return payloads


def _build_request(event: Event, payloads: list[dict]) -> dict:
    import json

    tool = {
        "name": "explain_teams",
        "description": "Return a structured rationale for each team.",
        "input_schema": {
            "type": "object",
            "properties": {
                "rationales": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "team_id": {"type": "string"},
                            "title": {"type": "string"},
                            "summary": {"type": "string"},
                            "strengths": {"type": "array", "items": {"type": "string"}},
                            "gaps": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["team_id", "title", "summary", "strengths", "gaps"],
                    },
                }
            },
            "required": ["rationales"],
        },
    }
    return {
        "model": settings.RATIONALE_MODEL,
        "max_tokens": _MAX_TOKENS,
        "system": [{
            "type": "text",
            "text": _SYSTEM_INSTRUCTIONS,
            "cache_control": {"type": "ephemeral"},
        }],
        "tools": [tool],
        "tool_choice": {"type": "tool", "name": "explain_teams"},
        "messages": [{
            "role": "user",
            "content": (
                f"Event: {event.title}\nDescription: {event.description or '(none)'}\n\n"
                f"Explain each team from this composition (JSON):\n{json.dumps(payloads)}"
            ),
        }],
    }


_REQUIRED_KEYS = {"team_id", "title", "summary", "strengths", "gaps"}


def _parse_rationales(content_blocks) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for block in content_blocks:
        if getattr(block, "type", None) == "tool_use":
            for r in block.input.get("rationales", []):
                if _REQUIRED_KEYS.issubset(r) and r["team_id"]:
                    out[r["team_id"]] = {
                        "title": r["title"], "summary": r["summary"],
                        "strengths": list(r["strengths"]), "gaps": list(r["gaps"]),
                    }
    return out


def _classify(event: Event, payloads: list[dict]) -> dict[str, dict]:
    """Call Claude for all teams; return {team_id: rationale}. Raises on failure."""
    import anthropic

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    msg = client.messages.create(**_build_request(event, payloads))
    return _parse_rationales(msg.content)


def generate(db: Session, allocation: Allocation) -> dict[str, dict]:
    """Generate + persist a rationale per team. Raises RationaleUnavailable with no key."""
    if not settings.ANTHROPIC_API_KEY:
        raise RationaleUnavailable("AI rationale requires ANTHROPIC_API_KEY")
    event = db.query(Event).filter(Event.id == allocation.event_id).first()
    payloads = _team_payloads(db, allocation)

    mapping: dict[str, dict] = {}
    try:
        mapping = _classify(event, payloads)
    except Exception as exc:  # noqa: BLE001 — best-effort; teams without a rationale just stay null
        logger.warning("Rationale generation failed: %s", exc)

    teams = db.query(Team).filter(Team.allocation_id == allocation.id).all()
    for team in teams:
        r = mapping.get(str(team.id))
        if r:
            team.rationale = r
    db.commit()
    return mapping
