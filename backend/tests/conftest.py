import hashlib
import json
import os
import time

import pytest
from coincurve import PrivateKey
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app

SQLALCHEMY_TEST_URL = "sqlite:///./test_squadsync.db"

engine = create_engine(SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def make_nostr_event(privkey: PrivateKey, url: str = "http://testserver/auth/nostr") -> dict:
    pubkey = privkey.public_key.format(compressed=True)[1:].hex()
    event = {
        "pubkey": pubkey,
        "created_at": int(time.time()),
        "kind": 27235,
        "tags": [["u", url], ["method", "POST"], ["nonce", os.urandom(8).hex()]],
        "content": "",
    }
    serialized = json.dumps(
        [0, event["pubkey"], event["created_at"], event["kind"], event["tags"], event["content"]],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    event_id = hashlib.sha256(serialized.encode()).hexdigest()
    event["id"] = event_id
    event["sig"] = privkey.sign_schnorr(bytes.fromhex(event_id)).hex()
    return event


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
def nostr_privkey():
    return PrivateKey()


@pytest.fixture
def auth_headers(client, nostr_privkey):
    pubkey = nostr_privkey.public_key.format(compressed=True)[1:].hex()
    event = make_nostr_event(nostr_privkey)
    res = client.post("/auth/nostr", json={"pubkey": pubkey, "event": event})
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
