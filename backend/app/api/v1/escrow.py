"""Escrow agent discovery and publishing endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.escrow_agent import EscrowAgentEvent
from app.models.user import User
from app.services import nostr_service, pip01
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


def _agent_out(event: dict) -> dict:
    """Convert a raw Nostr event into an agent summary for the API response."""
    parsed = pip01.parse_escrow_event(event)
    coordinate = pip01.escrow_coordinate_from_event(event)
    return {
        "coordinate": coordinate,
        "pubkey": event.get("pubkey", ""),
        "escrow_type": parsed.escrow_type,
        "networks": parsed.networks,
        "funding_rules": parsed.funding_rules,
        "release_rules": parsed.release_rules,
        "dispute_rules": parsed.dispute_rules,
        "reference_format": parsed.reference_format,
        "content": parsed.model_dump() if parsed else None,
    }


@router.get("/agents")
def list_agents(db: Session = Depends(get_db)):
    """Return escrow agents discovered from Nostr relays (cached)."""
    relay_events = nostr_service.fetch_escrow_agents()
    relay_agents = [_agent_out(e) for e in relay_events]

    local_agents = [
        _agent_out(row.event_json)
        for row in db.query(EscrowAgentEvent).order_by(EscrowAgentEvent.created_at.desc()).all()
    ]

    seen = set()
    merged = []
    for agent in local_agents + relay_agents:
        if agent["coordinate"] not in seen:
            seen.add(agent["coordinate"])
            merged.append(agent)

    return {"agents": merged}


@router.post("/agents", status_code=status.HTTP_200_OK)
def refresh_agents():
    """Force-refresh the escrow agent cache from Nostr relays."""
    nostr_service.refresh_escrow_agents()
    return {"status": "ok"}


@router.post("/publish", status_code=status.HTTP_201_CREATED)
def publish_agent(
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Accept a signed kind-30361 event, publish to relays, and store locally."""
    event = body.get("event")
    if not isinstance(event, dict):
        raise HTTPException(status_code=422, detail="Missing event object")

    if event.get("kind") != pip01.PIP01_ESCROW_KIND:
        raise HTTPException(
            status_code=422,
            detail=f"Expected kind {pip01.PIP01_ESCROW_KIND}, got {event.get('kind')}",
        )

    if event.get("pubkey") != current_user.pubkey:
        raise HTTPException(
            status_code=403,
            detail="Event pubkey does not match authenticated user",
        )

    pubkey = current_user.pubkey
    coordinate = pip01.escrow_coordinate_from_event(event)

    existing = (
        db.query(EscrowAgentEvent)
        .filter(EscrowAgentEvent.coordinate == coordinate)
        .first()
    )
    if existing:
        existing.event_json = event
    else:
        db.add(
            EscrowAgentEvent(
                user_id=current_user.id,
                coordinate=coordinate,
                event_json=event,
            )
        )

    db.commit()
    nostr_service.publish_event(event)

    return {"coordinate": coordinate, "status": "published"}
