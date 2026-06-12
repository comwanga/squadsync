import csv
import io
from uuid import UUID

from fastapi import HTTPException
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.allocation import Allocation
from app.models.participant import Participant
from app.models.team import Team, TeamMember


def _get_published_allocation(db: Session, allocation_id: UUID) -> Allocation:
    allocation = db.query(Allocation).filter(Allocation.id == allocation_id).first()
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")
    if allocation.status != "published":
        raise HTTPException(status_code=400, detail="Allocation not yet published")
    return allocation


def _get_teams_with_members(db: Session, allocation_id: UUID):
    teams = db.query(Team).filter(Team.allocation_id == allocation_id).all()
    result = []
    for team in teams:
        members = (
            db.query(Participant)
            .join(TeamMember, Participant.id == TeamMember.participant_id)
            .filter(TeamMember.team_id == team.id)
            .all()
        )
        result.append((team, members))
    return result


def generate_csv(db: Session, allocation_id: UUID) -> bytes:
    _get_published_allocation(db, allocation_id)
    teams_data = _get_teams_with_members(db, allocation_id)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Team", "Name", "Email", "Role", "Skill Level", "Years Experience", "Fairness Score"])
    for team, members in teams_data:
        for m in members:
            writer.writerow([
                team.name, m.name, m.email, m.role,
                m.skill_level, m.years_experience, team.fairness_score,
            ])
    return buf.getvalue().encode("utf-8")


def generate_pdf(db: Session, allocation_id: UUID) -> bytes:
    _get_published_allocation(db, allocation_id)
    teams_data = _get_teams_with_members(db, allocation_id)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("SquadSync — Team Allocation", styles["Title"]))
    elements.append(Spacer(1, 12))

    for team, members in teams_data:
        elements.append(Paragraph(f"{team.name} (Fairness: {team.fairness_score}%)", styles["Heading2"]))
        table_data = [["Name", "Email", "Role", "Skill", "Experience"]]
        for m in members:
            table_data.append([m.name, m.email, m.role, m.skill_level, f"{m.years_experience}y"])
        t = Table(table_data, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d4ed8")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 16))

    doc.build(elements)
    return buf.getvalue()


def generate_share_link(allocation_id: UUID) -> str:
    return f"{settings.FRONTEND_URL}/results/{allocation_id}"
