from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1 import auth, events, participants, allocation, teams, export

app = FastAPI(title="SquadSync API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
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


@app.get("/health")
def health():
    return {"status": "ok"}
