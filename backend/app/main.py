from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.api.v1 import auth, escrow, events, participants, allocation, teams, export, public, feedback, payouts, rationale
import app.models  # noqa: F401


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(title="SquadSync API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(events.router, prefix="/api/v1/events", tags=["events"])
app.include_router(participants.router, prefix="/api/v1/events", tags=["participants"])
app.include_router(allocation.router, prefix="/api/v1/events", tags=["allocation"])
app.include_router(teams.router, prefix="/api/v1/allocations", tags=["teams"])
app.include_router(export.router, prefix="/api/v1/allocations", tags=["export"])
app.include_router(public.router, prefix="/api/v1/public", tags=["public"])
app.include_router(feedback.router, prefix="/api/v1/feedback", tags=["feedback"])
app.include_router(payouts.router, prefix="/api/v1/allocations", tags=["payouts"])
app.include_router(rationale.router, prefix="/api/v1/allocations", tags=["rationale"])
app.include_router(escrow.router, prefix="/api/v1/escrow", tags=["escrow"])


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ready"}
