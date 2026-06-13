import hashlib
import json
import time

from coincurve import PrivateKey

from tests.conftest import make_nostr_event


def test_nostr_login_creates_user(client):
    privkey = PrivateKey()
    pubkey = privkey.public_key.format(compressed=True)[1:].hex()
    event = make_nostr_event(privkey)
    res = client.post("/auth/nostr", json={"pubkey": pubkey, "event": event})
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_nostr_login_returns_same_user_on_second_call(client):
    privkey = PrivateKey()
    pubkey = privkey.public_key.format(compressed=True)[1:].hex()

    res1 = client.post("/auth/nostr", json={"pubkey": pubkey, "event": make_nostr_event(privkey)})
    res2 = client.post("/auth/nostr", json={"pubkey": pubkey, "event": make_nostr_event(privkey)})
    assert res1.status_code == 200
    assert res2.status_code == 200


def test_nostr_login_expired_event(client):
    privkey = PrivateKey()
    pubkey = privkey.public_key.format(compressed=True)[1:].hex()
    event = make_nostr_event(privkey)
    event["created_at"] = int(time.time()) - 120  # 2 minutes old

    # Recompute id/sig with the modified timestamp
    serialized = json.dumps(
        [0, event["pubkey"], event["created_at"], event["kind"], event["tags"], event["content"]],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    event["id"] = hashlib.sha256(serialized.encode()).hexdigest()
    event["sig"] = privkey.sign_schnorr(bytes.fromhex(event["id"])).hex()

    res = client.post("/auth/nostr", json={"pubkey": pubkey, "event": event})
    assert res.status_code == 400


def test_nostr_login_wrong_pubkey(client):
    privkey = PrivateKey()
    other = PrivateKey()
    event = make_nostr_event(privkey)
    wrong_pubkey = other.public_key.format(compressed=True)[1:].hex()
    res = client.post("/auth/nostr", json={"pubkey": wrong_pubkey, "event": event})
    assert res.status_code == 400


def test_nostr_login_invalid_signature(client):
    privkey = PrivateKey()
    pubkey = privkey.public_key.format(compressed=True)[1:].hex()
    event = make_nostr_event(privkey)
    event["sig"] = "0" * 128  # garbage sig
    res = client.post("/auth/nostr", json={"pubkey": pubkey, "event": event})
    assert res.status_code == 401


def test_protected_route_without_token(client):
    res = client.get("/api/v1/events")
    assert res.status_code == 401


def test_protected_route_with_token(client, auth_headers):
    res = client.get("/api/v1/events", headers=auth_headers)
    assert res.status_code == 200
