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


def bech32_decode(bech: str) -> tuple[str, bytes]:
    """Decode a bech32 `npub`/`nsec` to (hrp, 32-byte key).

    Minimal decoder: splits on the last '1', drops the 6-char checksum, and
    converts the 5-bit data groups to 8-bit bytes. Sufficient for npub/nsec.
    """
    bech = bech.strip().lower()
    pos = bech.rfind("1")
    if pos < 1:
        raise ValueError("invalid bech32 string")
    hrp = bech[:pos]
    try:
        data = [_BECH32_CHARSET.index(c) for c in bech[pos + 1:]]
    except ValueError as exc:
        raise ValueError("invalid bech32 character") from exc
    data = data[:-6]  # drop checksum
    acc = 0
    bits = 0
    out = bytearray()
    for value in data:
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
