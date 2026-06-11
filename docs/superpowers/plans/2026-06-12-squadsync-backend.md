# SquadSync Phase 1 — Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete SquadSync FastAPI backend — auth, event management, QR registration, 4-pass allocation engine, and CSV/PDF/link export — deployed as a Dockerized service with PostgreSQL.

**Architecture:** FastAPI app with SQLAlchemy 2.0 ORM and Alembic migrations. Auth uses JWT (python-jose) with bcrypt passwords and Google OAuth token verification. The allocation engine runs synchronously in-process. Tests use pytest + httpx AsyncClient against a SQLite in-memory database.

**Tech Stack:** Python 3.12, FastAPI 0.111+, SQLAlchemy 2.0, Pydantic v2, Alembic, python-jose, passlib[bcrypt], google-auth, reportlab, qrcode[pil], pytest, pytest-asyncio, httpx

---

## File Map

| File | Responsibility |
|------|----------------|
| `backend/requirements.txt` | All Python dependencies |
| `backend/Dockerfile` | Production container |
| `backend/.env.example` | Required env vars |
| `backend/alembic.ini` | Alembic config |
| `backend/alembic/env.py` | Alembic migration env |
| `backend/alembic/versions/001_initial.py` | Initial schema |
| `backend/app/main.py` | App factory, CORS, router mounts |
| `backend/app/core/config.py` | Settings from env (pydantic-settings) |
| `backend/app/core/database.py` | SQLAlchemy engine + session |
| `backend/app/core/security.py` | Password hashing, JWT encode/decode |
| `backend/app/models/__init__.py` | Re-exports all models (for Alembic) |
| `backend/app/models/user.py` | User ORM model |
| `backend/app/models/event.py` | Event + EventCoOrganizer ORM models |
| `backend/app/models/participant.py` | Participant ORM model |
| `backend/app/models/allocation.py` | AllocationConfig + Allocation ORM models |
| `backend/app/models/team.py` | Team + TeamMember ORM models |
| `backend/app/schemas/auth.py` | Register/Login/Token Pydantic schemas |
| `backend/app/schemas/event.py` | Event CRUD Pydantic schemas |
| `backend/app/schemas/participant.py` | Participant Pydantic schemas |
| `backend/app/schemas/allocation.py` | AllocationConfig + Allocation + Team schemas |
| `backend/app/api/deps.py` | `get_db`, `get_current_user` dependencies |
| `backend/app/api/v1/auth.py` | Auth routes |
| `backend/app/api/v1/events.py` | Event CRUD + co-organizer routes |
| `backend/app/api/v1/participants.py` | Participant list + delete |
| `backend/app/api/v1/allocation.py` | Config + allocate + publish routes |
| `backend/app/api/v1/teams.py` | Team list + detail routes |
| `backend/app/api/v1/export.py` | CSV, PDF, share link routes |
| `backend/app/services/auth_service.py` | Register, login, Google OAuth logic |
| `backend/app/services/allocation_engine.py` | 4-pass algorithm + scoring |
| `backend/app/services/export_service.py` | CSV/PDF generation, share link creation |
| `backend/tests/conftest.py` | pytest fixtures: DB, client, user, event |
| `backend/tests/test_auth.py` | Auth endpoint tests |
| `backend/tests/test_events.py` | Event CRUD + co-organizer tests |
| `backend/tests/test_registration.py` | Public registration tests |
| `backend/tests/test_allocation_engine.py` | Engine unit tests |
| `backend/tests/test_export.py` | Export endpoint tests |

---

## Task 1: Monorepo Root + Docker Compose

**Files:**
- Create: `docker-compose.yml`
- Create: `.gitignore`
- Create: `backend/.env.example`
- Create: `backend/requirements.txt`
- Create: `backend/Dockerfile`

- [ ] **Step 1: Create `.gitignore`**

```
# Python
__pycache__/
*.pyc
.venv/
*.egg-info/
dist/
.pytest_cache/
.mypy_cache/

# Node
node_modules/
.next/
.vercel/

# Env
.env
.env.local
*.env

# DB
*.db
*.sqlite

# OS
.DS_Store
Thumbs.db
```

- [ ] **Step 2: Create `backend/requirements.txt`**

```
fastapi==0.111.0
uvicorn[standard]==0.30.1
sqlalchemy==2.0.30
alembic==1.13.1
pydantic==2.7.1
pydantic-settings==2.3.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
httpx==0.27.0
python-multipart==0.0.9
google-auth==2.30.0
requests==2.32.3
reportlab==4.2.0
qrcode[pil]==7.4.2
Pillow==10.3.0
aiosqlite==0.20.0
pytest==8.2.2
pytest-asyncio==0.23.7
anyio==4.4.0
```

- [ ] **Step 3: Create `backend/.env.example`**

```
DATABASE_URL=postgresql+psycopg2://squadsync:password@localhost:5432/squadsync
SECRET_KEY=change-me-to-a-long-random-string
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
GOOGLE_CLIENT_ID=your-google-client-id
FRONTEND_URL=http://localhost:3000
```

- [ ] **Step 4: Create `backend/Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 5: Create `docker-compose.yml` at repo root**

```yaml
version: "3.9"

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: squadsync
      POSTGRES_PASSWORD: password
      POSTGRES_DB: squadsync
    ports:
      - "5432:5432"
    volumes:
      - pg_data:/var/lib/postgresql/data

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+psycopg2://squadsync:password@db:5432/squadsync
      SECRET_KEY: dev-secret-key
      ALGORITHM: HS256
      ACCESS_TOKEN_EXPIRE_MINUTES: 1440
      GOOGLE_CLIENT_ID: ""
      FRONTEND_URL: http://localhost:3000
    depends_on:
      - db
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

volumes:
  pg_data:
```

- [ ] **Step 6: Commit**

```bash
git add .gitignore docker-compose.yml backend/requirements.txt backend/Dockerfile backend/.env.example
git commit -m "chore: monorepo root + docker-compose + backend scaffold"
```

---

## Task 2: Backend Core (Config, Database, Security, App Factory)

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/database.py`
- Create: `backend/app/core/security.py`
- Create: `backend/app/main.py`

- [ ] **Step 1: Create `backend/app/core/config.py`**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    GOOGLE_CLIENT_ID: str = ""
    FRONTEND_URL: str = "http://localhost:3000"

    class Config:
        env_file = ".env"


settings = Settings()
```

- [ ] **Step 2: Create `backend/app/core/database.py`**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


engine = create_engine(settings.DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 3: Create `backend/app/core/security.py`**

```python
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(sub: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": sub, "exp": expire}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> str:
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    sub: str = payload.get("sub")
    if sub is None:
        raise JWTError("No sub in token")
    return sub
```

- [ ] **Step 4: Create `backend/app/main.py`**

```python
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
```

- [ ] **Step 5: Create empty `__init__.py` files**

```bash
touch backend/app/__init__.py
touch backend/app/core/__init__.py
touch backend/app/models/__init__.py
touch backend/app/schemas/__init__.py
touch backend/app/api/__init__.py
touch backend/app/api/v1/__init__.py
touch backend/app/services/__init__.py
touch backend/tests/__init__.py
```

- [ ] **Step 6: Verify app starts**

```bash
cd backend
python -m pip install -r requirements.txt
DATABASE_URL=sqlite:///./test.db SECRET_KEY=testsecret uvicorn app.main:app --port 8000
```

Expected: `Application startup complete.` at `http://localhost:8000/health` → `{"status":"ok"}`

- [ ] **Step 7: Commit**

```bash
git add backend/app/
git commit -m "feat: FastAPI core bootstrap (config, database, security, app factory)"
```

---

## Task 3: SQLAlchemy Models

**Files:**
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/event.py`
- Create: `backend/app/models/participant.py`
- Create: `backend/app/models/allocation.py`
- Create: `backend/app/models/team.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Create `backend/app/models/user.py`**

```python
import uuid
from sqlalchemy import Column, String, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy import DateTime

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=True)
    provider = Column(SAEnum("local", "google", name="user_provider"), nullable=False, default="local")
    provider_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 2: Create `backend/app/models/event.py`**

```python
import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, Enum as SAEnum, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    participant_limit = Column(Integer, nullable=True)
    team_count = Column(Integer, nullable=False)
    status = Column(
        SAEnum("draft", "active", "allocated", "archived", name="event_status"),
        nullable=False,
        default="draft",
    )
    registration_slug = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EventCoOrganizer(Base):
    __tablename__ = "event_co_organizers"

    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    invited_at = Column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 3: Create `backend/app/models/participant.py`**

```python
import uuid
from sqlalchemy import Column, String, Integer, Float, ForeignKey, Enum as SAEnum, DateTime, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class Participant(Base):
    __tablename__ = "participants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    skill_level = Column(
        SAEnum("beginner", "intermediate", "advanced", "professional", name="skill_level"),
        nullable=False,
    )
    role = Column(
        SAEnum(
            "frontend", "backend", "fullstack", "ai_ml", "ux", "devops",
            "blockchain", "mobile", "product", "marketing", name="participant_role",
        ),
        nullable=False,
    )
    years_experience = Column(Integer, nullable=False, default=0)
    tech_stack = Column(ARRAY(String), nullable=False, default=list)
    interests = Column(ARRAY(String), nullable=False, default=list)
    composite_score = Column(Float, nullable=True)
    registered_at = Column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 4: Create `backend/app/models/allocation.py`**

```python
import uuid
from sqlalchemy import Column, String, Float, ForeignKey, Enum as SAEnum, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.core.database import Base


class AllocationConfig(Base):
    __tablename__ = "allocation_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), unique=True, nullable=False)
    weight_experience = Column(Float, nullable=False, default=0.5)
    weight_skill = Column(Float, nullable=False, default=0.5)
    role_constraints = Column(JSONB, nullable=False, default=dict)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Allocation(Base):
    __tablename__ = "allocations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False, index=True)
    snapshot_hash = Column(String, nullable=False)
    status = Column(
        SAEnum("draft", "published", name="allocation_status"),
        nullable=False,
        default="draft",
    )
    constraint_warnings = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 5: Create `backend/app/models/team.py`**

```python
import uuid
from sqlalchemy import Column, String, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Team(Base):
    __tablename__ = "teams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    allocation_id = Column(UUID(as_uuid=True), ForeignKey("allocations.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    fairness_score = Column(Float, nullable=True)
    skill_score = Column(Float, nullable=True)
    role_balance_score = Column(Float, nullable=True)


class TeamMember(Base):
    __tablename__ = "team_members"

    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), primary_key=True)
    participant_id = Column(UUID(as_uuid=True), ForeignKey("participants.id"), primary_key=True)
```

- [ ] **Step 6: Update `backend/app/models/__init__.py`**

```python
from app.models.user import User
from app.models.event import Event, EventCoOrganizer
from app.models.participant import Participant
from app.models.allocation import AllocationConfig, Allocation
from app.models.team import Team, TeamMember

__all__ = [
    "User", "Event", "EventCoOrganizer", "Participant",
    "AllocationConfig", "Allocation", "Team", "TeamMember",
]
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/
git commit -m "feat: SQLAlchemy ORM models (users, events, participants, allocations, teams)"
```

---

## Task 4: Alembic Migration

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/001_initial.py`

- [ ] **Step 1: Initialize Alembic**

```bash
cd backend
alembic init alembic
```

- [ ] **Step 2: Update `backend/alembic/env.py`** — replace the `target_metadata` section

```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

from app.core.config import settings
from app.core.database import Base
import app.models  # noqa: F401 — ensures all models are registered

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 3: Generate migration**

```bash
cd backend
DATABASE_URL=postgresql+psycopg2://squadsync:password@localhost:5432/squadsync alembic revision --autogenerate -m "initial schema"
```

Expected: `Generating .../alembic/versions/xxxx_initial_schema.py ... done`

- [ ] **Step 4: Apply migration**

```bash
DATABASE_URL=postgresql+psycopg2://squadsync:password@localhost:5432/squadsync alembic upgrade head
```

Expected: `Running upgrade  -> xxxx, initial schema`

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/
git commit -m "feat: initial Alembic schema migration"
```

---

## Task 5: Pydantic Schemas

**Files:**
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/schemas/event.py`
- Create: `backend/app/schemas/participant.py`
- Create: `backend/app/schemas/allocation.py`

- [ ] **Step 1: Create `backend/app/schemas/auth.py`**

```python
from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    token: str  # Google ID token


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    provider: str

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Create `backend/app/schemas/event.py`**

```python
from typing import Optional
from pydantic import BaseModel


class EventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    participant_limit: Optional[int] = None
    team_count: int


class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    participant_limit: Optional[int] = None
    team_count: Optional[int] = None
    status: Optional[str] = None


class EventOut(BaseModel):
    id: str
    owner_id: str
    title: str
    description: Optional[str]
    participant_limit: Optional[int]
    team_count: int
    status: str
    registration_slug: str

    model_config = {"from_attributes": True}


class CoOrganizerInvite(BaseModel):
    email: str
```

- [ ] **Step 3: Create `backend/app/schemas/participant.py`**

```python
from typing import Optional
from pydantic import BaseModel, EmailStr


class ParticipantRegister(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    skill_level: str
    role: str
    years_experience: int = 0
    tech_stack: list[str] = []
    interests: list[str] = []


class ParticipantOut(BaseModel):
    id: str
    event_id: str
    name: str
    email: str
    phone: Optional[str]
    skill_level: str
    role: str
    years_experience: int
    tech_stack: list[str]
    interests: list[str]
    composite_score: Optional[float]

    model_config = {"from_attributes": True}


class EventPublicInfo(BaseModel):
    id: str
    title: str
    description: Optional[str]
    participant_limit: Optional[int]
    status: str

    model_config = {"from_attributes": True}
```

- [ ] **Step 4: Create `backend/app/schemas/allocation.py`**

```python
from typing import Optional
from pydantic import BaseModel


class AllocationConfigIn(BaseModel):
    weight_experience: float = 0.5
    weight_skill: float = 0.5
    role_constraints: dict[str, int] = {}


class AllocationConfigOut(BaseModel):
    id: str
    event_id: str
    weight_experience: float
    weight_skill: float
    role_constraints: dict

    model_config = {"from_attributes": True}


class TeamMemberOut(BaseModel):
    id: str
    name: str
    email: str
    role: str
    skill_level: str
    composite_score: Optional[float]

    model_config = {"from_attributes": True}


class TeamOut(BaseModel):
    id: str
    allocation_id: str
    name: str
    fairness_score: Optional[float]
    skill_score: Optional[float]
    role_balance_score: Optional[float]
    members: list[TeamMemberOut] = []

    model_config = {"from_attributes": True}


class AllocationOut(BaseModel):
    id: str
    event_id: str
    snapshot_hash: str
    status: str
    constraint_warnings: dict
    teams: list[TeamOut] = []

    model_config = {"from_attributes": True}
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/
git commit -m "feat: Pydantic v2 schemas (auth, event, participant, allocation)"
```

---

## Task 6: Auth Service + Routes

**Files:**
- Create: `backend/app/api/deps.py`
- Create: `backend/app/services/auth_service.py`
- Create: `backend/app/api/v1/auth.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_auth.py`

- [ ] **Step 1: Write failing auth tests**

Create `backend/tests/conftest.py`:

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app

SQLALCHEMY_TEST_URL = "sqlite:///./test_squadsync.db"

engine = create_engine(SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def override_get_db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def registered_user(client):
    client.post("/auth/register", json={
        "name": "Test User",
        "email": "test@example.com",
        "password": "password123"
    })
    return {"email": "test@example.com", "password": "password123"}


@pytest.fixture
def auth_headers(client, registered_user):
    res = client.post("/auth/login", json=registered_user)
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
```

Create `backend/tests/test_auth.py`:

```python
def test_register_success(client):
    res = client.post("/auth/register", json={
        "name": "Alice",
        "email": "alice@example.com",
        "password": "secret123"
    })
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_register_duplicate_email(client):
    payload = {"name": "Alice", "email": "alice@example.com", "password": "secret123"}
    client.post("/auth/register", json=payload)
    res = client.post("/auth/register", json=payload)
    assert res.status_code == 400


def test_login_success(client, registered_user):
    res = client.post("/auth/login", json=registered_user)
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_login_wrong_password(client, registered_user):
    res = client.post("/auth/login", json={"email": registered_user["email"], "password": "wrong"})
    assert res.status_code == 401


def test_protected_route_without_token(client):
    res = client.get("/api/v1/events")
    assert res.status_code == 401


def test_protected_route_with_token(client, auth_headers):
    res = client.get("/api/v1/events", headers=auth_headers)
    assert res.status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
pytest tests/test_auth.py -v
```

Expected: `ImportError` or `404` failures — routes not implemented yet.

- [ ] **Step 3: Create `backend/app/api/deps.py`**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        user_id = decode_token(credentials.credentials)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
```

- [ ] **Step 4: Create `backend/app/services/auth_service.py`**

```python
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest


def register_user(db: Session, req: RegisterRequest) -> str:
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    user = User(
        name=req.name,
        email=req.email,
        hashed_password=hash_password(req.password),
        provider="local",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return create_access_token(str(user.id))


def login_user(db: Session, req: LoginRequest) -> str:
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not user.hashed_password or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return create_access_token(str(user.id))
```

- [ ] **Step 5: Create `backend/app/api/v1/auth.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserOut
from app.services.auth_service import register_user, login_user

router = APIRouter()


@router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    token = register_user(db, req)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    token = login_user(db, req)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
def me(current_user=Depends(get_current_user)):
    return current_user
```

- [ ] **Step 6: Add stub `events` router so protected route test passes**

Create `backend/app/api/v1/events.py` (stub — full implementation in Task 7):

```python
from fastapi import APIRouter, Depends
from app.api.deps import get_current_user

router = APIRouter()


@router.get("")
def list_events(current_user=Depends(get_current_user)):
    return []
```

Create stubs for remaining routers:

```bash
# Create stub files
cat > backend/app/api/v1/participants.py << 'EOF'
from fastapi import APIRouter
router = APIRouter()
EOF

cat > backend/app/api/v1/allocation.py << 'EOF'
from fastapi import APIRouter
router = APIRouter()
EOF

cat > backend/app/api/v1/teams.py << 'EOF'
from fastapi import APIRouter
router = APIRouter()
EOF

cat > backend/app/api/v1/export.py << 'EOF'
from fastapi import APIRouter
router = APIRouter()
EOF
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
cd backend
pytest tests/test_auth.py -v
```

Expected: All 6 tests `PASSED`.

- [ ] **Step 8: Commit**

```bash
git add backend/app/api/ backend/app/services/auth_service.py backend/tests/
git commit -m "feat: auth service + routes + tests (register, login, JWT)"
```

---

## Task 7: Google OAuth Route

**Files:**
- Modify: `backend/app/services/auth_service.py`
- Modify: `backend/app/api/v1/auth.py`
- Modify: `backend/tests/test_auth.py`

- [ ] **Step 1: Add Google OAuth test**

Append to `backend/tests/test_auth.py`:

```python
from unittest.mock import patch


def test_google_oauth_new_user(client):
    mock_idinfo = {
        "sub": "google-uid-123",
        "email": "googleuser@gmail.com",
        "name": "Google User",
    }
    with patch("app.services.auth_service.verify_google_token", return_value=mock_idinfo):
        res = client.post("/auth/google", json={"token": "fake-google-token"})
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_google_oauth_existing_user(client):
    mock_idinfo = {
        "sub": "google-uid-123",
        "email": "googleuser@gmail.com",
        "name": "Google User",
    }
    with patch("app.services.auth_service.verify_google_token", return_value=mock_idinfo):
        client.post("/auth/google", json={"token": "fake-google-token"})
        res = client.post("/auth/google", json={"token": "fake-google-token"})
    assert res.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_auth.py::test_google_oauth_new_user -v
```

Expected: `404 Not Found`

- [ ] **Step 3: Add `verify_google_token` + `google_login` to `backend/app/services/auth_service.py`**

```python
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from app.core.config import settings


def verify_google_token(token: str) -> dict:
    return id_token.verify_oauth2_token(token, google_requests.Request(), settings.GOOGLE_CLIENT_ID)


def google_login(db: Session, token: str) -> str:
    idinfo = verify_google_token(token)
    google_sub = idinfo["sub"]
    email = idinfo["email"]
    name = idinfo.get("name", email)

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(name=name, email=email, provider="google", provider_id=google_sub)
        db.add(user)
        db.commit()
        db.refresh(user)
    return create_access_token(str(user.id))
```

- [ ] **Step 4: Add route to `backend/app/api/v1/auth.py`**

```python
from app.schemas.auth import GoogleAuthRequest
from app.services.auth_service import google_login


@router.post("/google", response_model=TokenResponse)
def google_auth(req: GoogleAuthRequest, db: Session = Depends(get_db)):
    token = google_login(db, req.token)
    return TokenResponse(access_token=token)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_auth.py -v
```

Expected: All 8 tests `PASSED`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/auth_service.py backend/app/api/v1/auth.py backend/tests/test_auth.py
git commit -m "feat: Google OAuth route + auth service"
```

---

## Task 8: Event CRUD + Co-Organizer Routes

**Files:**
- Create: `backend/app/services/event_service.py`
- Modify: `backend/app/api/v1/events.py`
- Create: `backend/tests/test_events.py`

- [ ] **Step 1: Write failing event tests**

Create `backend/tests/test_events.py`:

```python
def test_create_event(client, auth_headers):
    res = client.post("/api/v1/events", headers=auth_headers, json={
        "title": "Hackathon 2026",
        "team_count": 10
    })
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Hackathon 2026"
    assert "registration_slug" in data
    assert len(data["registration_slug"]) == 8


def test_list_events_empty(client, auth_headers):
    res = client.get("/api/v1/events", headers=auth_headers)
    assert res.status_code == 200
    assert res.json() == []


def test_list_events_returns_own(client, auth_headers):
    client.post("/api/v1/events", headers=auth_headers, json={"title": "E1", "team_count": 5})
    res = client.get("/api/v1/events", headers=auth_headers)
    assert len(res.json()) == 1


def test_get_event(client, auth_headers):
    created = client.post("/api/v1/events", headers=auth_headers, json={"title": "E1", "team_count": 5}).json()
    res = client.get(f"/api/v1/events/{created['id']}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["id"] == created["id"]


def test_update_event(client, auth_headers):
    created = client.post("/api/v1/events", headers=auth_headers, json={"title": "Old", "team_count": 5}).json()
    res = client.patch(f"/api/v1/events/{created['id']}", headers=auth_headers, json={"title": "New"})
    assert res.status_code == 200
    assert res.json()["title"] == "New"


def test_delete_event_archives_it(client, auth_headers):
    created = client.post("/api/v1/events", headers=auth_headers, json={"title": "E1", "team_count": 5}).json()
    res = client.delete(f"/api/v1/events/{created['id']}", headers=auth_headers)
    assert res.status_code == 200
    detail = client.get(f"/api/v1/events/{created['id']}", headers=auth_headers).json()
    assert detail["status"] == "archived"


def test_invite_co_organizer(client, auth_headers):
    # Register second user
    client.post("/auth/register", json={"name": "Bob", "email": "bob@example.com", "password": "pass123"})
    created = client.post("/api/v1/events", headers=auth_headers, json={"title": "E1", "team_count": 5}).json()
    res = client.post(
        f"/api/v1/events/{created['id']}/co-organizers",
        headers=auth_headers,
        json={"email": "bob@example.com"}
    )
    assert res.status_code == 200


def test_co_organizer_can_view_event(client, auth_headers):
    client.post("/auth/register", json={"name": "Bob", "email": "bob@example.com", "password": "pass123"})
    bob_token = client.post("/auth/login", json={"email": "bob@example.com", "password": "pass123"}).json()["access_token"]
    bob_headers = {"Authorization": f"Bearer {bob_token}"}

    created = client.post("/api/v1/events", headers=auth_headers, json={"title": "E1", "team_count": 5}).json()
    client.post(f"/api/v1/events/{created['id']}/co-organizers", headers=auth_headers, json={"email": "bob@example.com"})

    res = client.get(f"/api/v1/events/{created['id']}", headers=bob_headers)
    assert res.status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_events.py -v
```

Expected: Multiple `AssertionError` — routes not implemented.

- [ ] **Step 3: Create `backend/app/services/event_service.py`**

```python
import secrets
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.event import Event, EventCoOrganizer
from app.models.user import User
from app.schemas.event import EventCreate, EventUpdate, CoOrganizerInvite


def _generate_slug() -> str:
    return secrets.token_urlsafe(6)[:8]


def _assert_organizer(db: Session, event_id: UUID, user_id: UUID) -> Event:
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    is_owner = str(event.owner_id) == str(user_id)
    is_co = db.query(EventCoOrganizer).filter(
        EventCoOrganizer.event_id == event_id,
        EventCoOrganizer.user_id == user_id,
    ).first() is not None
    if not (is_owner or is_co):
        raise HTTPException(status_code=403, detail="Not authorized")
    return event


def create_event(db: Session, req: EventCreate, owner_id: UUID) -> Event:
    slug = _generate_slug()
    while db.query(Event).filter(Event.registration_slug == slug).first():
        slug = _generate_slug()
    event = Event(**req.model_dump(), owner_id=owner_id, registration_slug=slug)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_events(db: Session, user_id: UUID) -> list[Event]:
    owned = db.query(Event).filter(Event.owner_id == user_id, Event.status != "archived").all()
    co_event_ids = [
        row.event_id for row in db.query(EventCoOrganizer).filter(EventCoOrganizer.user_id == user_id).all()
    ]
    co_events = db.query(Event).filter(Event.id.in_(co_event_ids), Event.status != "archived").all()
    seen = {str(e.id) for e in owned}
    return owned + [e for e in co_events if str(e.id) not in seen]


def get_event(db: Session, event_id: UUID, user_id: UUID) -> Event:
    return _assert_organizer(db, event_id, user_id)


def update_event(db: Session, event_id: UUID, user_id: UUID, req: EventUpdate) -> Event:
    event = _assert_organizer(db, event_id, user_id)
    for field, value in req.model_dump(exclude_none=True).items():
        setattr(event, field, value)
    db.commit()
    db.refresh(event)
    return event


def delete_event(db: Session, event_id: UUID, user_id: UUID) -> Event:
    event = _assert_organizer(db, event_id, user_id)
    event.status = "archived"
    db.commit()
    db.refresh(event)
    return event


def invite_co_organizer(db: Session, event_id: UUID, user_id: UUID, req: CoOrganizerInvite) -> None:
    _assert_organizer(db, event_id, user_id)
    invitee = db.query(User).filter(User.email == req.email).first()
    if not invitee:
        raise HTTPException(status_code=404, detail="User not found")
    existing = db.query(EventCoOrganizer).filter(
        EventCoOrganizer.event_id == event_id,
        EventCoOrganizer.user_id == invitee.id,
    ).first()
    if not existing:
        db.add(EventCoOrganizer(event_id=event_id, user_id=invitee.id))
        db.commit()


def remove_co_organizer(db: Session, event_id: UUID, owner_id: UUID, co_user_id: UUID) -> None:
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event or str(event.owner_id) != str(owner_id):
        raise HTTPException(status_code=403, detail="Only owner can remove co-organizers")
    db.query(EventCoOrganizer).filter(
        EventCoOrganizer.event_id == event_id,
        EventCoOrganizer.user_id == co_user_id,
    ).delete()
    db.commit()
```

- [ ] **Step 4: Replace `backend/app/api/v1/events.py`**

```python
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.event import EventCreate, EventUpdate, EventOut, CoOrganizerInvite
from app.services.event_service import (
    create_event, list_events, get_event, update_event, delete_event,
    invite_co_organizer, remove_co_organizer,
)

router = APIRouter()


@router.post("", response_model=EventOut, status_code=status.HTTP_201_CREATED)
def create(req: EventCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return create_event(db, req, current_user.id)


@router.get("", response_model=list[EventOut])
def list_all(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return list_events(db, current_user.id)


@router.get("/{event_id}", response_model=EventOut)
def get(event_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return get_event(db, event_id, current_user.id)


@router.patch("/{event_id}", response_model=EventOut)
def update(event_id: UUID, req: EventUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return update_event(db, event_id, current_user.id, req)


@router.delete("/{event_id}", response_model=EventOut)
def delete(event_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return delete_event(db, event_id, current_user.id)


@router.post("/{event_id}/co-organizers")
def invite(event_id: UUID, req: CoOrganizerInvite, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    invite_co_organizer(db, event_id, current_user.id, req)
    return {"detail": "invited"}


@router.delete("/{event_id}/co-organizers/{co_user_id}")
def remove(event_id: UUID, co_user_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    remove_co_organizer(db, event_id, current_user.id, co_user_id)
    return {"detail": "removed"}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_events.py -v
```

Expected: All 8 tests `PASSED`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/event_service.py backend/app/api/v1/events.py backend/tests/test_events.py
git commit -m "feat: event CRUD + co-organizer invite routes + tests"
```

---

## Task 9: Public Registration + Participant Routes

**Files:**
- Create: `backend/app/services/registration_service.py`
- Modify: `backend/app/api/v1/participants.py`
- Create: `backend/tests/test_registration.py`

- [ ] **Step 1: Write failing registration tests**

Create `backend/tests/test_registration.py`:

```python
import pytest


@pytest.fixture
def active_event(client, auth_headers):
    event = client.post("/api/v1/events", headers=auth_headers, json={"title": "Hackathon", "team_count": 3}).json()
    client.patch(f"/api/v1/events/{event['id']}", headers=auth_headers, json={"status": "active"})
    return event


def test_get_public_event_info(client, active_event):
    slug = active_event["registration_slug"]
    res = client.get(f"/api/v1/events/{slug}/info")
    assert res.status_code == 200
    assert res.json()["title"] == "Hackathon"


def test_register_participant(client, active_event):
    slug = active_event["registration_slug"]
    res = client.post(f"/api/v1/events/{slug}/register", json={
        "name": "Alice",
        "email": "alice@example.com",
        "skill_level": "intermediate",
        "role": "frontend",
        "years_experience": 3
    })
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Alice"
    assert data["composite_score"] is not None


def test_composite_score_computed_correctly(client, active_event):
    slug = active_event["registration_slug"]
    res = client.post(f"/api/v1/events/{slug}/register", json={
        "name": "Bob",
        "email": "bob@example.com",
        "skill_level": "advanced",   # K=3
        "role": "backend",
        "years_experience": 5        # E=3
    })
    # Default weights 0.5 each: Sc = (0.5*3) + (0.5*3) = 3.0
    assert res.json()["composite_score"] == pytest.approx(3.0)


def test_duplicate_registration_rejected(client, active_event):
    slug = active_event["registration_slug"]
    payload = {"name": "Alice", "email": "alice@example.com", "skill_level": "beginner", "role": "ux", "years_experience": 0}
    client.post(f"/api/v1/events/{slug}/register", json=payload)
    res = client.post(f"/api/v1/events/{slug}/register", json=payload)
    assert res.status_code == 400


def test_list_participants(client, auth_headers, active_event):
    slug = active_event["registration_slug"]
    client.post(f"/api/v1/events/{slug}/register", json={
        "name": "Alice", "email": "alice@example.com", "skill_level": "beginner", "role": "ux", "years_experience": 0
    })
    res = client.get(f"/api/v1/events/{active_event['id']}/participants", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()) == 1


def test_delete_participant(client, auth_headers, active_event):
    slug = active_event["registration_slug"]
    p = client.post(f"/api/v1/events/{slug}/register", json={
        "name": "Alice", "email": "alice@example.com", "skill_level": "beginner", "role": "ux", "years_experience": 0
    }).json()
    res = client.delete(f"/api/v1/events/{active_event['id']}/participants/{p['id']}", headers=auth_headers)
    assert res.status_code == 200
    remaining = client.get(f"/api/v1/events/{active_event['id']}/participants", headers=auth_headers).json()
    assert len(remaining) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_registration.py -v
```

Expected: `404` or `AssertionError` — routes not implemented.

- [ ] **Step 3: Create `backend/app/services/registration_service.py`**

```python
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.participant import Participant
from app.schemas.participant import ParticipantRegister


_EXP_MAP = {0: 1, 1: 1, 2: 2, 3: 2, 4: 3, 5: 3, 6: 3}
_SKILL_MAP = {"beginner": 1, "intermediate": 2, "advanced": 3, "professional": 4}


def compute_composite_score(years_exp: int, skill_level: str, w_exp: float = 0.5, w_skill: float = 0.5) -> float:
    e = _EXP_MAP.get(min(years_exp, 6), 4 if years_exp >= 7 else 1)
    k = _SKILL_MAP[skill_level]
    return round((w_exp * e) + (w_skill * k), 4)


def get_public_event(db: Session, slug: str) -> Event:
    event = db.query(Event).filter(Event.registration_slug == slug).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


def register_participant(db: Session, slug: str, req: ParticipantRegister) -> Participant:
    event = get_public_event(db, slug)
    if event.status not in ("active",):
        raise HTTPException(status_code=400, detail="Event is not accepting registrations")

    if event.participant_limit:
        count = db.query(Participant).filter(Participant.event_id == event.id).count()
        if count >= event.participant_limit:
            raise HTTPException(status_code=400, detail="Event is full")

    existing = db.query(Participant).filter(
        Participant.event_id == event.id,
        Participant.email == req.email,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered for this event")

    score = compute_composite_score(req.years_experience, req.skill_level)
    participant = Participant(
        event_id=event.id,
        composite_score=score,
        **req.model_dump(),
    )
    db.add(participant)
    db.commit()
    db.refresh(participant)
    return participant


def list_participants(db: Session, event_id: UUID, user_id: UUID, role: str = None, skill: str = None) -> list[Participant]:
    from app.services.event_service import _assert_organizer
    _assert_organizer(db, event_id, user_id)
    q = db.query(Participant).filter(Participant.event_id == event_id)
    if role:
        q = q.filter(Participant.role == role)
    if skill:
        q = q.filter(Participant.skill_level == skill)
    return q.all()


def delete_participant(db: Session, event_id: UUID, participant_id: UUID, user_id: UUID) -> Participant:
    from app.services.event_service import _assert_organizer
    _assert_organizer(db, event_id, user_id)
    p = db.query(Participant).filter(Participant.id == participant_id, Participant.event_id == event_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Participant not found")
    db.delete(p)
    db.commit()
    return p
```

- [ ] **Step 4: Replace `backend/app/api/v1/participants.py`**

```python
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.participant import ParticipantRegister, ParticipantOut, EventPublicInfo
from app.services.registration_service import (
    get_public_event, register_participant, list_participants, delete_participant,
)

router = APIRouter()


@router.get("/{slug}/info", response_model=EventPublicInfo)
def public_info(slug: str, db: Session = Depends(get_db)):
    return get_public_event(db, slug)


@router.post("/{slug}/register", response_model=ParticipantOut, status_code=status.HTTP_201_CREATED)
def register(slug: str, req: ParticipantRegister, db: Session = Depends(get_db)):
    return register_participant(db, slug, req)


@router.get("/{event_id}/participants", response_model=list[ParticipantOut])
def list_all(
    event_id: UUID,
    role: Optional[str] = Query(None),
    skill: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_participants(db, event_id, current_user.id, role, skill)


@router.delete("/{event_id}/participants/{participant_id}", response_model=ParticipantOut)
def delete(
    event_id: UUID,
    participant_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return delete_participant(db, event_id, participant_id, current_user.id)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_registration.py -v
```

Expected: All 6 tests `PASSED`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/registration_service.py backend/app/api/v1/participants.py backend/tests/test_registration.py
git commit -m "feat: public registration + participant management routes + tests"
```

---

## Task 10: Allocation Engine

**Files:**
- Create: `backend/app/services/allocation_engine.py`
- Modify: `backend/app/api/v1/allocation.py`
- Create: `backend/tests/test_allocation_engine.py`

- [ ] **Step 1: Write failing engine unit tests**

Create `backend/tests/test_allocation_engine.py`:

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.event import Event
from app.models.participant import Participant
from app.models.allocation import AllocationConfig, Allocation
from app.models.team import Team, TeamMember
from app.models.user import User
from app.services.allocation_engine import run_allocation, compute_composite_score
import uuid

TEST_DB = "sqlite:///./test_engine.db"
engine = create_engine(TEST_DB, connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)


@pytest.fixture(autouse=True)
def setup():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db():
    s = Session()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture
def owner(db):
    u = User(name="Owner", email="owner@test.com", provider="local", hashed_password="x")
    db.add(u)
    db.commit()
    return u


@pytest.fixture
def event(db, owner):
    e = Event(owner_id=owner.id, title="Test Event", team_count=3, registration_slug="testslug", status="active")
    db.add(e)
    db.commit()
    return e


@pytest.fixture
def config(db, event):
    c = AllocationConfig(event_id=event.id, weight_experience=0.5, weight_skill=0.5, role_constraints={})
    db.add(c)
    db.commit()
    return c


def add_participant(db, event_id, skill, role, years):
    p = Participant(
        event_id=event_id,
        name=f"{role}-{skill}",
        email=f"{role}{skill}{uuid.uuid4().hex[:4]}@test.com",
        skill_level=skill,
        role=role,
        years_experience=years,
        tech_stack=[],
        interests=[],
    )
    db.add(p)
    db.commit()
    return p


# Composite score formula tests
def test_score_beginner_no_experience():
    assert compute_composite_score(0, "beginner", 0.5, 0.5) == pytest.approx(1.0)


def test_score_professional_senior():
    # E=4 (7+y), K=4 (professional): Sc = 0.5*4 + 0.5*4 = 4.0
    assert compute_composite_score(10, "professional", 0.5, 0.5) == pytest.approx(4.0)


def test_score_advanced_midlevel():
    # E=3 (4-6y), K=3 (advanced): Sc = 0.5*3 + 0.5*3 = 3.0
    assert compute_composite_score(5, "advanced", 0.5, 0.5) == pytest.approx(3.0)


def test_score_custom_weights():
    # E=2, K=1, w_exp=0.8, w_skill=0.2: Sc = 0.8*2 + 0.2*1 = 1.8
    assert compute_composite_score(2, "beginner", 0.8, 0.2) == pytest.approx(1.8)


# Engine tests
def test_allocation_creates_correct_team_count(db, event, config):
    for i in range(9):
        add_participant(db, event.id, "intermediate", "frontend", 3)
    allocation = run_allocation(db, event.id, config)
    teams = db.query(Team).filter(Team.allocation_id == allocation.id).all()
    assert len(teams) == 3


def test_allocation_all_participants_assigned(db, event, config):
    for _ in range(9):
        add_participant(db, event.id, "beginner", "backend", 0)
    allocation = run_allocation(db, event.id, config)
    assigned = db.query(TeamMember).join(Team).filter(Team.allocation_id == allocation.id).count()
    assert assigned == 9


def test_allocation_anchors_distributed(db, event, config):
    # 3 professionals → one per team
    for _ in range(3):
        add_participant(db, event.id, "professional", "fullstack", 10)
    for _ in range(6):
        add_participant(db, event.id, "beginner", "frontend", 0)
    allocation = run_allocation(db, event.id, config)
    teams = db.query(Team).filter(Team.allocation_id == allocation.id).all()
    # Each team should have exactly 1 professional anchor + 2 beginners
    for team in teams:
        members = db.query(Participant).join(TeamMember, Participant.id == TeamMember.participant_id)\
            .filter(TeamMember.team_id == team.id).all()
        pro_count = sum(1 for m in members if m.skill_level == "professional")
        assert pro_count == 1


def test_allocation_role_constraint_warning(db, event, config):
    # Require frontend but provide none
    config.role_constraints = {"frontend": 1}
    db.commit()
    for _ in range(3):
        add_participant(db, event.id, "intermediate", "backend", 3)
    allocation = run_allocation(db, event.id, config)
    assert allocation.constraint_warnings  # should have warnings


def test_allocation_role_constraint_satisfied(db, event, config):
    config.role_constraints = {"frontend": 1}
    db.commit()
    # One frontend per team
    for _ in range(3):
        add_participant(db, event.id, "intermediate", "frontend", 3)
    for _ in range(6):
        add_participant(db, event.id, "intermediate", "backend", 3)
    allocation = run_allocation(db, event.id, config)
    assert allocation.constraint_warnings == {}


def test_allocation_no_participants_raises(db, event, config):
    from fastapi import HTTPException
    with pytest.raises(HTTPException, match="No participants"):
        run_allocation(db, event.id, config)


def test_allocation_more_teams_than_participants_raises(db, event, config):
    from fastapi import HTTPException
    add_participant(db, event.id, "beginner", "frontend", 0)  # only 1, but 3 teams
    with pytest.raises(HTTPException, match="Fewer participants"):
        run_allocation(db, event.id, config)


def test_fairness_scores_stored(db, event, config):
    for _ in range(6):
        add_participant(db, event.id, "intermediate", "backend", 3)
    allocation = run_allocation(db, event.id, config)
    teams = db.query(Team).filter(Team.allocation_id == allocation.id).all()
    for team in teams:
        assert team.fairness_score is not None
        assert 0 <= team.fairness_score <= 100


def test_snapshot_hash_deterministic(db, event, config):
    for _ in range(6):
        add_participant(db, event.id, "intermediate", "backend", 3)
    a1 = run_allocation(db, event.id, config)
    # Mark as draft and run again (same participants)
    a2 = run_allocation(db, event.id, config)
    assert a1.snapshot_hash == a2.snapshot_hash
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_allocation_engine.py -v
```

Expected: `ImportError` — service not implemented.

- [ ] **Step 3: Create `backend/app/services/allocation_engine.py`**

```python
import hashlib
import statistics
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.allocation import AllocationConfig, Allocation
from app.models.event import Event
from app.models.participant import Participant
from app.models.team import Team, TeamMember

_EXP_MAP = {0: 1, 1: 1, 2: 2, 3: 2, 4: 3, 5: 3, 6: 3}
_SKILL_MAP = {"beginner": 1, "intermediate": 2, "advanced": 3, "professional": 4}


def compute_composite_score(years_exp: int, skill_level: str, w_exp: float = 0.5, w_skill: float = 0.5) -> float:
    e = _EXP_MAP.get(min(years_exp, 6), 4 if years_exp >= 7 else 1)
    k = _SKILL_MAP[skill_level]
    return round((w_exp * e) + (w_skill * k), 4)


def run_allocation(db: Session, event_id: UUID, config: AllocationConfig) -> Allocation:
    participants = db.query(Participant).filter(Participant.event_id == event_id).all()
    if not participants:
        raise HTTPException(status_code=400, detail="No participants to allocate")

    event = db.query(Event).filter(Event.id == event_id).first()
    n_teams = event.team_count
    if n_teams > len(participants):
        raise HTTPException(status_code=400, detail="Fewer participants than teams")

    # Recompute composite scores with current weights
    for p in participants:
        p.composite_score = compute_composite_score(
            p.years_experience, p.skill_level,
            config.weight_experience, config.weight_skill,
        )
    db.flush()

    # Snapshot hash
    sorted_ids = sorted([str(p.id) for p in participants])
    snapshot_hash = hashlib.sha256(",".join(sorted_ids).encode()).hexdigest()

    # Team buckets
    buckets: list[dict] = [
        {"members": [], "score_sum": 0.0, "roles": []}
        for _ in range(n_teams)
    ]
    unassigned: set = {p.id for p in participants}

    # Pass 1: Anchors (Sc >= 3.0)
    anchors = sorted(
        [p for p in participants if p.composite_score >= 3.0],
        key=lambda x: -x.composite_score,
    )
    for i, anchor in enumerate(anchors):
        idx = i % n_teams
        buckets[idx]["members"].append(anchor)
        buckets[idx]["score_sum"] += anchor.composite_score
        buckets[idx]["roles"].append(anchor.role)
        unassigned.discard(anchor.id)

    # Pass 2: Intermediates (1.5 <= Sc < 3.0)
    intermediates = sorted(
        [p for p in participants if p.id in unassigned and 1.5 <= p.composite_score < 3.0],
        key=lambda x: -x.composite_score,
    )
    for p in intermediates:
        idx = min(range(n_teams), key=lambda i: buckets[i]["score_sum"])
        buckets[idx]["members"].append(p)
        buckets[idx]["score_sum"] += p.composite_score
        buckets[idx]["roles"].append(p.role)
        unassigned.discard(p.id)

    # Pass 3: Role constraint enforcement
    role_constraints: dict = config.role_constraints or {}
    constraint_warnings: dict = {}
    remaining_pool = [p for p in participants if p.id in unassigned]

    if role_constraints:
        for i, bucket in enumerate(buckets):
            team_key = f"team_{i + 1:02d}"
            for role, min_count in role_constraints.items():
                current = bucket["roles"].count(role)
                needed = min_count - current
                for _ in range(needed):
                    candidates = [p for p in remaining_pool if p.role == role]
                    if candidates:
                        c = candidates[0]
                        remaining_pool.remove(c)
                        bucket["members"].append(c)
                        bucket["score_sum"] += c.composite_score
                        bucket["roles"].append(c.role)
                        unassigned.discard(c.id)
                    else:
                        constraint_warnings.setdefault(team_key, []).append(f"missing: {role}")

    # Pass 4: Beginner fill
    remaining = [p for p in participants if p.id in unassigned]
    for p in remaining:
        idx = min(range(n_teams), key=lambda i: len(buckets[i]["members"]))
        buckets[idx]["members"].append(p)
        buckets[idx]["score_sum"] += p.composite_score
        buckets[idx]["roles"].append(p.role)

    # Compute global skill scores
    score_sums = [b["score_sum"] for b in buckets]
    mean_sc = statistics.mean(score_sums) if score_sums else 1.0
    std_sc = statistics.stdev(score_sums) if len(score_sums) > 1 else 0.0
    skill_score = max(0.0, 100 * (1 - std_sc / mean_sc)) if mean_sc else 0.0

    total_constraints = sum(n_teams * v for v in role_constraints.values()) if role_constraints else 0
    total_warnings = sum(len(v) for v in constraint_warnings.values())
    fulfilled = total_constraints - total_warnings
    role_balance_score = (100 * fulfilled / total_constraints) if total_constraints else 100.0
    fairness_score = (skill_score * 0.6) + (role_balance_score * 0.4)

    # Persist
    allocation = Allocation(
        event_id=event_id,
        snapshot_hash=snapshot_hash,
        status="draft",
        constraint_warnings=constraint_warnings,
    )
    db.add(allocation)
    db.flush()

    for i, bucket in enumerate(buckets):
        team = Team(
            allocation_id=allocation.id,
            name=f"Team {i + 1:02d}",
            skill_score=round(skill_score, 1),
            role_balance_score=round(role_balance_score, 1),
            fairness_score=round(fairness_score, 1),
        )
        db.add(team)
        db.flush()
        for member in bucket["members"]:
            db.add(TeamMember(team_id=team.id, participant_id=member.id))

    db.commit()
    db.refresh(allocation)
    return allocation
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_allocation_engine.py -v
```

Expected: All 11 tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/allocation_engine.py backend/tests/test_allocation_engine.py
git commit -m "feat: 4-pass allocation engine + unit tests"
```

---

## Task 11: Allocation Config + API Routes

**Files:**
- Modify: `backend/app/api/v1/allocation.py`
- Modify: `backend/app/api/v1/teams.py`

- [ ] **Step 1: Replace `backend/app/api/v1/allocation.py`**

```python
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.allocation import AllocationConfig, Allocation
from app.schemas.allocation import AllocationConfigIn, AllocationConfigOut, AllocationOut, TeamOut, TeamMemberOut
from app.services.allocation_engine import run_allocation
from app.services.event_service import _assert_organizer
from app.models.team import Team, TeamMember
from app.models.participant import Participant

router = APIRouter()


def _build_allocation_out(db: Session, allocation: Allocation) -> AllocationOut:
    teams_orm = db.query(Team).filter(Team.allocation_id == allocation.id).all()
    teams_out = []
    for team in teams_orm:
        members_orm = (
            db.query(Participant)
            .join(TeamMember, Participant.id == TeamMember.participant_id)
            .filter(TeamMember.team_id == team.id)
            .all()
        )
        members_out = [TeamMemberOut.model_validate(m) for m in members_orm]
        teams_out.append(TeamOut(
            id=str(team.id),
            allocation_id=str(team.allocation_id),
            name=team.name,
            fairness_score=team.fairness_score,
            skill_score=team.skill_score,
            role_balance_score=team.role_balance_score,
            members=members_out,
        ))
    return AllocationOut(
        id=str(allocation.id),
        event_id=str(allocation.event_id),
        snapshot_hash=allocation.snapshot_hash,
        status=allocation.status,
        constraint_warnings=allocation.constraint_warnings,
        teams=teams_out,
    )


@router.get("/{event_id}/config", response_model=AllocationConfigOut)
def get_config(event_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _assert_organizer(db, event_id, current_user.id)
    config = db.query(AllocationConfig).filter(AllocationConfig.event_id == event_id).first()
    if not config:
        config = AllocationConfig(event_id=event_id)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


@router.put("/{event_id}/config", response_model=AllocationConfigOut)
def update_config(
    event_id: UUID,
    req: AllocationConfigIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_organizer(db, event_id, current_user.id)
    if abs(req.weight_experience + req.weight_skill - 1.0) > 0.001:
        raise HTTPException(status_code=400, detail="Weights must sum to 1.0")
    config = db.query(AllocationConfig).filter(AllocationConfig.event_id == event_id).first()
    if not config:
        config = AllocationConfig(event_id=event_id)
        db.add(config)
    config.weight_experience = req.weight_experience
    config.weight_skill = req.weight_skill
    config.role_constraints = req.role_constraints
    db.commit()
    db.refresh(config)
    return config


@router.post("/{event_id}/allocate", response_model=AllocationOut)
def allocate(event_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _assert_organizer(db, event_id, current_user.id)
    config = db.query(AllocationConfig).filter(AllocationConfig.event_id == event_id).first()
    if not config:
        config = AllocationConfig(event_id=event_id)
        db.add(config)
        db.commit()
    allocation = run_allocation(db, event_id, config)
    return _build_allocation_out(db, allocation)


@router.get("/{event_id}/allocations/{allocation_id}", response_model=AllocationOut)
def get_allocation(
    event_id: UUID,
    allocation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_organizer(db, event_id, current_user.id)
    allocation = db.query(Allocation).filter(
        Allocation.id == allocation_id, Allocation.event_id == event_id
    ).first()
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")
    return _build_allocation_out(db, allocation)


@router.post("/{event_id}/allocations/{allocation_id}/publish")
def publish_allocation(
    event_id: UUID,
    allocation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_organizer(db, event_id, current_user.id)
    allocation = db.query(Allocation).filter(
        Allocation.id == allocation_id, Allocation.event_id == event_id
    ).first()
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")
    allocation.status = "published"
    db.commit()
    return {"detail": "published"}
```

- [ ] **Step 2: Replace `backend/app/api/v1/teams.py`**

```python
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.allocation import Allocation
from app.models.team import Team, TeamMember
from app.models.participant import Participant
from app.schemas.allocation import TeamOut, TeamMemberOut

router = APIRouter()


@router.get("/{allocation_id}/teams", response_model=list[TeamOut])
def list_teams(allocation_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    teams = db.query(Team).filter(Team.allocation_id == allocation_id).all()
    result = []
    for team in teams:
        members = (
            db.query(Participant)
            .join(TeamMember, Participant.id == TeamMember.participant_id)
            .filter(TeamMember.team_id == team.id)
            .all()
        )
        result.append(TeamOut(
            id=str(team.id),
            allocation_id=str(team.allocation_id),
            name=team.name,
            fairness_score=team.fairness_score,
            skill_score=team.skill_score,
            role_balance_score=team.role_balance_score,
            members=[TeamMemberOut.model_validate(m) for m in members],
        ))
    return result


@router.get("/{allocation_id}/teams/{team_id}", response_model=TeamOut)
def get_team(allocation_id: UUID, team_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    team = db.query(Team).filter(Team.id == team_id, Team.allocation_id == allocation_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    members = (
        db.query(Participant)
        .join(TeamMember, Participant.id == TeamMember.participant_id)
        .filter(TeamMember.team_id == team.id)
        .all()
    )
    return TeamOut(
        id=str(team.id),
        allocation_id=str(team.allocation_id),
        name=team.name,
        fairness_score=team.fairness_score,
        skill_score=team.skill_score,
        role_balance_score=team.role_balance_score,
        members=[TeamMemberOut.model_validate(m) for m in members],
    )
```

- [ ] **Step 3: Run all tests**

```bash
pytest tests/ -v
```

Expected: All tests `PASSED`.

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/v1/allocation.py backend/app/api/v1/teams.py
git commit -m "feat: allocation config + allocate + publish + team detail routes"
```

---

## Task 12: Export Service + Routes

**Files:**
- Create: `backend/app/services/export_service.py`
- Modify: `backend/app/api/v1/export.py`
- Create: `backend/tests/test_export.py`

- [ ] **Step 1: Write failing export tests**

Create `backend/tests/test_export.py`:

```python
import pytest


@pytest.fixture
def published_allocation(client, auth_headers):
    # Create event
    event = client.post("/api/v1/events", headers=auth_headers, json={"title": "H2026", "team_count": 2}).json()
    client.patch(f"/api/v1/events/{event['id']}", headers=auth_headers, json={"status": "active"})
    slug = event["registration_slug"]

    # Register 4 participants
    for i, (skill, role, years) in enumerate([
        ("advanced", "frontend", 4),
        ("intermediate", "backend", 2),
        ("beginner", "ux", 0),
        ("professional", "fullstack", 8),
    ]):
        client.post(f"/api/v1/events/{slug}/register", json={
            "name": f"Person{i}", "email": f"p{i}@test.com",
            "skill_level": skill, "role": role, "years_experience": years
        })

    # Run and publish allocation
    alloc = client.post(f"/api/v1/events/{event['id']}/allocate", headers=auth_headers).json()
    client.post(f"/api/v1/events/{event['id']}/allocations/{alloc['id']}/publish", headers=auth_headers)
    return alloc


def test_export_csv(client, auth_headers, published_allocation):
    res = client.get(f"/api/v1/allocations/{published_allocation['id']}/export/csv", headers=auth_headers)
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    content = res.text
    assert "Team" in content
    assert "Person" in content


def test_export_pdf(client, auth_headers, published_allocation):
    res = client.get(f"/api/v1/allocations/{published_allocation['id']}/export/pdf", headers=auth_headers)
    assert res.status_code == 200
    assert "application/pdf" in res.headers["content-type"]
    assert res.content[:4] == b"%PDF"


def test_export_share_link(client, auth_headers, published_allocation):
    res = client.get(f"/api/v1/allocations/{published_allocation['id']}/export/link", headers=auth_headers)
    assert res.status_code == 200
    assert "url" in res.json()
    assert published_allocation["id"] in res.json()["url"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_export.py -v
```

Expected: `404` — routes not implemented.

- [ ] **Step 3: Create `backend/app/services/export_service.py`**

```python
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
```

- [ ] **Step 4: Replace `backend/app/api/v1/export.py`**

```python
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.services.export_service import generate_csv, generate_pdf, generate_share_link

router = APIRouter()


@router.get("/{allocation_id}/export/csv")
def export_csv(allocation_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    data = generate_csv(db, allocation_id)
    return Response(content=data, media_type="text/csv", headers={
        "Content-Disposition": f"attachment; filename=squadsync-{allocation_id}.csv"
    })


@router.get("/{allocation_id}/export/pdf")
def export_pdf(allocation_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    data = generate_pdf(db, allocation_id)
    return Response(content=data, media_type="application/pdf", headers={
        "Content-Disposition": f"attachment; filename=squadsync-{allocation_id}.pdf"
    })


@router.get("/{allocation_id}/export/link")
def export_link(allocation_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    url = generate_share_link(allocation_id)
    return {"url": url}
```

- [ ] **Step 5: Run all tests**

```bash
pytest tests/ -v
```

Expected: All tests `PASSED`.

- [ ] **Step 6: Run full test suite with coverage**

```bash
pytest tests/ -v --tb=short
```

Expected: All green. Note any failures and fix before committing.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/export_service.py backend/app/api/v1/export.py backend/tests/test_export.py
git commit -m "feat: CSV + PDF + share link export service + routes + tests"
```

---

## Task 13: Docker Build Verification

**Files:** No new files.

- [ ] **Step 1: Build Docker image**

```bash
cd backend
docker build -t squadsync-backend:dev .
```

Expected: `Successfully built <image-id>`

- [ ] **Step 2: Verify health endpoint via Docker**

```bash
docker run --rm -e DATABASE_URL=sqlite:///./test.db -e SECRET_KEY=testsecret -p 8001:8000 squadsync-backend:dev &
sleep 3
curl http://localhost:8001/health
```

Expected: `{"status":"ok"}`

- [ ] **Step 3: Stop container and commit**

```bash
docker stop $(docker ps -q --filter ancestor=squadsync-backend:dev)
git add backend/Dockerfile
git commit -m "chore: verify Docker build and health endpoint"
```

---

## Final Backend Verification

- [ ] **Run the complete test suite**

```bash
cd backend
pytest tests/ -v --tb=short
```

Expected output:
```
tests/test_auth.py::test_register_success PASSED
tests/test_auth.py::test_register_duplicate_email PASSED
tests/test_auth.py::test_login_success PASSED
tests/test_auth.py::test_login_wrong_password PASSED
tests/test_auth.py::test_protected_route_without_token PASSED
tests/test_auth.py::test_protected_route_with_token PASSED
tests/test_auth.py::test_google_oauth_new_user PASSED
tests/test_auth.py::test_google_oauth_existing_user PASSED
tests/test_events.py::... (8 tests) PASSED
tests/test_registration.py::... (6 tests) PASSED
tests/test_allocation_engine.py::... (11 tests) PASSED
tests/test_export.py::... (3 tests) PASSED
```

- [ ] **Start backend locally against Docker Postgres**

```bash
cd backend
DATABASE_URL=postgresql+psycopg2://squadsync:password@localhost:5432/squadsync SECRET_KEY=devsecret uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs` — all endpoints visible in Swagger UI.
