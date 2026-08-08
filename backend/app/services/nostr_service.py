"""Best-effort Nostr NIP-04 DM sender.

Self-contained: decodes bech32 keys, encrypts/signs a kind-4 event, and
publishes it to relays. `send_dm` never raises and no-ops when unconfigured.
Personal secret keys must never be stored — `SQUADSYNC_NSEC` is a dedicated bot key.
"""
import base64
import hashlib
import json
import logging
import os
import time

from coincurve import PrivateKey, PublicKey
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from app.core.config import settings

logger = logging.getLogger(__name__)

_BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def _bech32_polymod(values: list[int]) -> int:
    """BIP-173 checksum polymod over hrp-expansion + data (incl. checksum)."""
    generator = (0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3)
    chk = 1
    for value in values:
        top = chk >> 25
        chk = ((chk & 0x1FFFFFF) << 5) ^ value
        for i in range(5):
            chk ^= generator[i] if ((top >> i) & 1) else 0
    return chk


def _bech32_hrp_expand(hrp: str) -> list[int]:
    return [ord(c) >> 5 for c in hrp] + [0] + [ord(c) & 31 for c in hrp]


def bech32_decode(bech: str) -> tuple[str, bytes]:
    """Decode a bech32 `npub`/`nsec` to (hrp, 32-byte key).

    Validates the BIP-173 checksum so a single mistyped character is rejected
    rather than silently decoded to a different (wrong) key. Sufficient for
    npub/nsec (bech32, not bech32m).
    """
    bech = bech.strip().lower()
    pos = bech.rfind("1")
    if pos < 1 or pos + 7 > len(bech):  # need a non-empty hrp + 6-char checksum
        raise ValueError("invalid bech32 string")
    hrp = bech[:pos]
    try:
        data = [_BECH32_CHARSET.index(c) for c in bech[pos + 1:]]
    except ValueError as exc:
        raise ValueError("invalid bech32 character") from exc
    if _bech32_polymod(_bech32_hrp_expand(hrp) + data) != 1:
        raise ValueError("invalid bech32 checksum")
    acc = 0
    bits = 0
    out = bytearray()
    for value in data[:-6]:  # drop the now-verified 6-char checksum
        acc = (acc << 5) | value
        bits += 5
        if bits >= 8:
            bits -= 8
            out.append((acc >> bits) & 0xFF)
    if bits >= 5 or (acc & ((1 << bits) - 1)):
        raise ValueError("invalid bech32 padding")
    return hrp, bytes(out)


def _shared_secret(privkey_bytes: bytes, peer_xonly: bytes) -> bytes:
    """secp256k1 ECDH raw-X shared secret (NIP-04).

    Reconstruct the peer point from its x-only key (assume even Y, the Nostr
    convention), multiply by our scalar, and take the raw 32-byte X coordinate.
    coincurve's `ecdh()` hashes the result, so we point-multiply instead.
    """
    peer_point = PublicKey(b"\x02" + peer_xonly)
    product = peer_point.multiply(privkey_bytes)
    return product.format(compressed=False)[1:33]


def encrypt_nip04(privkey_bytes: bytes, peer_xonly: bytes, message: str) -> str:
    """NIP-04 encrypt `message` → `base64(ciphertext)?iv=base64(iv)`."""
    key = _shared_secret(privkey_bytes, peer_xonly)
    iv = os.urandom(16)
    padder = padding.PKCS7(128).padder()
    data = padder.update(message.encode("utf-8")) + padder.finalize()
    encryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    ciphertext = encryptor.update(data) + encryptor.finalize()
    return base64.b64encode(ciphertext).decode() + "?iv=" + base64.b64encode(iv).decode()


def decrypt_nip04(privkey_bytes: bytes, peer_xonly: bytes, content: str) -> str:
    """Inverse of `encrypt_nip04` (used by tests to prove the round trip)."""
    key = _shared_secret(privkey_bytes, peer_xonly)
    b64_ct, b64_iv = content.split("?iv=")
    iv = base64.b64decode(b64_iv)
    ciphertext = base64.b64decode(b64_ct)
    decryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    return (unpadder.update(padded) + unpadder.finalize()).decode("utf-8")


def build_dm_event(privkey_bytes: bytes, recipient_xonly: bytes, message: str) -> dict:
    """Build a signed NIP-04 kind-4 DM event (NIP-01 serialization for the id)."""
    privkey = PrivateKey(privkey_bytes)
    pubkey_hex = privkey.public_key_xonly.format().hex()
    created_at = int(time.time())
    content = encrypt_nip04(privkey_bytes, recipient_xonly, message)
    tags = [["p", recipient_xonly.hex()]]

    serialized = json.dumps(
        [0, pubkey_hex, created_at, 4, tags, content],
        separators=(",", ":"),
        ensure_ascii=False,
    )
    event_id = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    sig = privkey.sign_schnorr(bytes.fromhex(event_id)).hex()

    return {
        "id": event_id,
        "pubkey": pubkey_hex,
        "created_at": created_at,
        "kind": 4,
        "tags": tags,
        "content": content,
        "sig": sig,
    }


def _publish_to_relays(event: dict, relays: list[str]) -> bool:
    """Open a short-lived websocket to each relay, send the EVENT, read one frame.

    Returns True if at least one relay *responded* (we don't parse the OK frame —
    delivery confirmation is out of scope). Per-relay errors are swallowed.
    Imported lazily so the rest of the module has no hard websockets dependency
    at import time (and tests monkeypatch this function).
    """
    from websockets.sync.client import connect

    payload = json.dumps(["EVENT", event])
    accepted = False
    for relay in relays:
        try:
            with connect(relay, open_timeout=5, close_timeout=5) as ws:
                ws.send(payload)
                ws.recv(timeout=5)  # best-effort: drain one frame (OK/NOTICE)
                accepted = True
        except Exception as exc:  # noqa: BLE001 — best-effort, never propagate
            logger.warning("Nostr relay %s rejected/failed: %s", relay, exc)
    return accepted


# --- Escrow agent discovery (kind 30361) ---

_escrow_cache: dict[str, list[dict]] = {}
_escrow_cache_ts: float = 0.0
_CACHE_TTL_SECONDS = 30
_REQUEST_TIMEOUT_MS = 8000


def _read_from_relays(relays: list[str], subscription_id: str, filter_obj: dict) -> list[dict]:
    """Open a short-lived WebSocket to each relay, REQ kind 30361, collect EVENTS.

    Returns deduplicated events (latest created_at wins per id) across all relays.
    Best-effort: a relay that times out is skipped; collected events from others
    are still returned.
    """
    from websockets.sync.client import connect

    events_by_id: dict[str, dict] = {}

    for relay in relays:
        try:
            with connect(relay, open_timeout=5, close_timeout=5) as ws:
                ws.send(json.dumps(["REQ", subscription_id, filter_obj]))
                remaining = _REQUEST_TIMEOUT_MS / 1000.0
                while remaining > 0:
                    try:
                        frame = ws.recv(timeout=min(remaining, 2))
                    except Exception:  # noqa: BLE001
                        break
                    remaining = _REQUEST_TIMEOUT_MS / 1000.0 - (time.time() - time.time())
                    try:
                        data = json.loads(frame)
                    except (json.JSONDecodeError, TypeError):
                        continue
                    if not isinstance(data, list):
                        continue
                    if data[0] == "EVENT" and data[1] == subscription_id:
                        event = data[2]
                        if isinstance(event, dict) and event.get("id"):
                            eid = event["id"]
                            if eid not in events_by_id or event.get("created_at", 0) > events_by_id[eid].get("created_at", 0):
                                events_by_id[eid] = event
                    if data[0] == "EOSE" and data[1] == subscription_id:
                        ws.send(json.dumps(["CLOSE", subscription_id]))
                        break
        except Exception as exc:  # noqa: BLE001
            logger.warning("Nostr relay %s read failed: %s", relay, exc)

    return sorted(events_by_id.values(), key=lambda e: e.get("created_at", 0), reverse=True)


def fetch_escrow_agents() -> list[dict]:
    """Return kind-30361 escrow descriptor events from Nostr relays.

    Results are cached for _CACHE_TTL_SECONDS to avoid hammering relays on
    every page load. Call refresh_escrow_agents() to force a fresh read.
    """
    global _escrow_cache, _escrow_cache_ts
    now = time.time()
    if _escrow_cache and (now - _escrow_cache_ts) < _CACHE_TTL_SECONDS:
        relay_key = settings.NOSTR_RELAYS
        if relay_key in _escrow_cache:
            return _escrow_cache[relay_key]

    return refresh_escrow_agents()


def refresh_escrow_agents() -> list[dict]:
    """Force-read escrow agents from all configured Nostr relays, bypassing the cache."""
    global _escrow_cache, _escrow_cache_ts
    relay_key = settings.NOSTR_RELAYS
    events = _read_from_relays(
        settings.nostr_relays,
        f"squadsync-escrow-{os.urandom(4).hex()}",
        {"kinds": [30361], "#t": ["escrow"], "limit": 50},
    )
    _escrow_cache[relay_key] = events
    _escrow_cache_ts = time.time()
    return events


def publish_event(event: dict) -> bool:
    """Publish a signed Nostr event to all configured relays.

    Returns True if at least one relay responded. Wraps _publish_to_relays
    so callers don't need to know the relay list.
    """
    return _publish_to_relays(event, settings.nostr_relays)


def send_dm(recipient_npub: str, message: str) -> bool:
    """Best-effort NIP-04 DM from the bot key to `recipient_npub`.

    No-ops (returns False) when `SQUADSYNC_NSEC` is unset. Never raises — all
    failures are logged and swallowed so callers (e.g. BackgroundTasks) are safe.
    """
    if not settings.SQUADSYNC_NSEC:
        logger.info("send_dm skipped: SQUADSYNC_NSEC not configured")
        return False
    try:
        _, privkey_bytes = bech32_decode(settings.SQUADSYNC_NSEC)
        _, recipient_xonly = bech32_decode(recipient_npub)
        event = build_dm_event(privkey_bytes, recipient_xonly, message)
        return _publish_to_relays(event, settings.nostr_relays)
    except Exception as exc:  # noqa: BLE001 — best-effort, never propagate
        logger.warning("send_dm failed: %s", exc)
        return False


def validate_npub(npub: str) -> str:
    """Return `npub` unchanged if it is a well-formed bech32 npub, else raise ValueError.

    A valid npub has hrp `npub` and decodes to a 32-byte key. `bech32_decode` already
    raises ValueError on malformed input (bad chars / no separator).
    """
    hrp, key = bech32_decode(npub)
    if hrp != "npub" or len(key) != 32:
        raise ValueError("invalid npub")
    return npub
