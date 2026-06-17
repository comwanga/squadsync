"""Best-effort team-notify fan-out: DM each npub-having attendee their team on publish.

Designed to run inside a FastAPI BackgroundTask (after the HTTP response is sent), so it
opens its OWN DB session. No-ops when SQUADSYNC_NSEC is unset (writes nothing, so enabling
the key later + re-publish still notifies). A dedup row is written ONLY on send success,
so a transient relay outage doesn't permanently suppress delivery — a later re-publish
retries. Per-participant failures are isolated and never abort the loop.
"""
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.allocation import Allocation
from app.models.event import Event
from app.models.participant import Participant
from app.models.team import Team, TeamMember
from app.models.team_notification import TeamNotification
from app.services.nostr_service import send_dm

logger = logging.getLogger(__name__)


def _results_link(allocation_id: UUID) -> str:
    origins = settings.cors_origins
    base = origins[0] if origins else settings.FRONTEND_URL.rstrip("/")
    return f"{base}/results/{allocation_id}"


def notify_teams_task(allocation_id: UUID) -> None:
    if not settings.SQUADSYNC_NSEC:
        return
    with SessionLocal() as db:
        allocation = db.query(Allocation).filter(Allocation.id == allocation_id).first()
        if not allocation or allocation.status != "published":
            return
        event = db.query(Event).filter(Event.id == allocation.event_id).first()
        event_title = event.title if event else "your event"
        link = _results_link(allocation_id)

        teams = db.query(Team).filter(Team.allocation_id == allocation.id).all()
        for team in teams:
            members = (
                db.query(Participant)
                .join(TeamMember, Participant.id == TeamMember.participant_id)
                .filter(TeamMember.team_id == team.id)
                .all()
            )
            for member in members:
                if not member.npub:
                    continue
                try:
                    already = (
                        db.query(TeamNotification)
                        .filter(
                            TeamNotification.allocation_id == allocation.id,
                            TeamNotification.participant_id == member.id,
                        )
                        .first()
                    )
                    if already:
                        continue
                    message = (
                        f"You're on {team.name} for {event_title}!\n\n"
                        f"See your team and teammates: {link}"
                    )
                    if not send_dm(member.npub, message):
                        logger.warning(
                            "Team DM not delivered for participant %s (allocation %s); will retry on re-publish",
                            member.id, allocation.id,
                        )
                        continue
                    db.add(TeamNotification(
                        allocation_id=allocation.id,
                        participant_id=member.id,
                        sent_at=datetime.now(timezone.utc),
                    ))
                    db.commit()
                except IntegrityError:
                    db.rollback()  # another writer already recorded this (allocation, participant)
                except Exception as exc:  # noqa: BLE001 — isolate per-participant failures
                    db.rollback()
                    logger.warning("Team notify failed for participant %s: %s", member.id, exc)
