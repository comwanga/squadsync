"""Nostr Wallet Connect (NIP-47) client — pay_invoice only.

Reuses nostr_service's NIP-04 encryption. The NWC URI carries the client's
secret key and the wallet service pubkey + relay:
    nostr+walletconnect://<wallet_pubkey_hex>?relay=<wss>&secret=<hex_privkey>

Flow over one short-lived websocket: subscribe (REQ) for the wallet's kind-23195
response tagged with our request id, publish the kind-23194 request, read frames
until the response arrives or we time out, decrypt it, return the preimage.

The NWC secret is a spend credential: it is used transiently and never persisted.
"""
import hashlib
import json
import logging
import time
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs

from coincurve import PrivateKey

from app.services.nostr_service import encrypt_nip04, decrypt_nip04

logger = logging.getLogger(__name__)

_REQUEST_KIND = 23194
_RESPONSE_KIND = 23195
_TIMEOUT = 30.0


class NwcError(Exception):
    """Any NWC failure: bad URI, wallet error response, or relay timeout."""


@dataclass
class NwcConnection:
    wallet_pubkey_hex: str   # x-only hex
    relay: str
    secret_bytes: bytes


def parse_nwc_uri(uri: str) -> NwcConnection:
    uri = uri.strip()
    if not uri.startswith("nostr+walletconnect://"):
        raise NwcError("not a nostr+walletconnect URI")
    parsed = urlparse(uri)
    wallet_pubkey = parsed.netloc or parsed.path.lstrip("/")
    qs = parse_qs(parsed.query)
    relay = (qs.get("relay") or [None])[0]
    secret_hex = (qs.get("secret") or [None])[0]
    if not wallet_pubkey or not relay or not secret_hex:
        raise NwcError("NWC URI missing wallet pubkey, relay, or secret")
    try:
        secret_bytes = bytes.fromhex(secret_hex)
    except ValueError as exc:
        raise NwcError("NWC secret is not valid hex") from exc
    return NwcConnection(wallet_pubkey_hex=wallet_pubkey.lower(), relay=relay, secret_bytes=secret_bytes)


def build_pay_invoice_request(secret_bytes: bytes, wallet_xonly: bytes, bolt11: str) -> dict:
    """Build a signed, NIP-04-encrypted kind-23194 pay_invoice request event."""
    privkey = PrivateKey(secret_bytes)
    pubkey_hex = privkey.public_key_xonly.format().hex()
    created_at = int(time.time())
    body = json.dumps({"method": "pay_invoice", "params": {"invoice": bolt11}},
                      separators=(",", ":"))
    content = encrypt_nip04(secret_bytes, wallet_xonly, body)
    tags = [["p", wallet_xonly.hex()]]
    serialized = json.dumps(
        [0, pubkey_hex, created_at, _REQUEST_KIND, tags, content],
        separators=(",", ":"), ensure_ascii=False,
    )
    event_id = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    sig = privkey.sign_schnorr(bytes.fromhex(event_id)).hex()
    return {"id": event_id, "pubkey": pubkey_hex, "created_at": created_at,
            "kind": _REQUEST_KIND, "tags": tags, "content": content, "sig": sig}


def decode_response(secret_bytes: bytes, wallet_xonly: bytes, content: str) -> dict:
    """Decrypt a kind-23195 response. Return {'preimage': ...} or raise NwcError."""
    plaintext = decrypt_nip04(secret_bytes, wallet_xonly, content)
    data = json.loads(plaintext)
    err = data.get("error")
    if err:
        # NIP-47 models error as {code, message}, but some wallets return a bare string.
        msg = err.get("message") if isinstance(err, dict) else str(err)
        raise NwcError(msg or "wallet returned an error")
    result = data.get("result") or {}
    preimage = result.get("preimage")
    if not preimage:
        raise NwcError("wallet response had no preimage")
    return {"preimage": preimage}


def _round_trip(conn: NwcConnection, request_event: dict) -> str:
    """Publish the request and read the wallet's response content. Monkeypatched in tests.

    Subscribe BEFORE publishing so we cannot miss a fast response. Returns the
    raw (still-encrypted) response event content; raises NwcError on timeout.
    """
    from websockets.sync.client import connect

    sub_id = request_event["id"][:16]
    req = json.dumps(["REQ", sub_id, {
        "kinds": [_RESPONSE_KIND],
        "authors": [conn.wallet_pubkey_hex],
        "#e": [request_event["id"]],
    }])
    event_msg = json.dumps(["EVENT", request_event])
    deadline = time.time() + _TIMEOUT
    try:
        with connect(conn.relay, open_timeout=10, close_timeout=5) as ws:
            ws.send(req)
            ws.send(event_msg)
            while time.time() < deadline:
                frame = json.loads(ws.recv(timeout=max(1.0, deadline - time.time())))
                if frame[0] == "EVENT" and frame[1] == sub_id:
                    return frame[2]["content"]
    except NwcError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise NwcError(f"NWC relay round-trip failed: {exc}") from exc
    raise NwcError("timed out waiting for wallet response")


def pay_invoice(uri: str, bolt11: str) -> str:
    """Pay `bolt11` via the wallet in `uri`. Return the payment preimage or raise NwcError."""
    conn = parse_nwc_uri(uri)
    wallet_xonly = bytes.fromhex(conn.wallet_pubkey_hex)
    request_event = build_pay_invoice_request(conn.secret_bytes, wallet_xonly, bolt11)
    content = _round_trip(conn, request_event)
    return decode_response(conn.secret_bytes, wallet_xonly, content)["preimage"]
