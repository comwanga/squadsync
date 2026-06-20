"""Test-only helpers for building Lightning artifacts.

`make_invoice` bech32-encodes a minimal bolt11 carrying a chosen payment hash so
tests can produce an invoice whose preimage they control. Only the payment-hash
tagged field is meaningful; the signature/checksum are zero-filled because the
production decoder (`app.services.bolt11`) reads the payment hash and nothing else.
"""
import hashlib

_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def _bytes_to_5bit(data: bytes) -> list[int]:
    acc = bits = 0
    out: list[int] = []
    for b in data:
        acc = (acc << 8) | b
        bits += 8
        while bits >= 5:
            bits -= 5
            out.append((acc >> bits) & 0x1F)
    if bits:
        out.append((acc << (5 - bits)) & 0x1F)
    return out


def make_invoice(payment_hash_hex: str) -> str:
    """Return a syntactically-walkable bolt11 carrying `payment_hash_hex` (32-byte hex)."""
    ph_groups = _bytes_to_5bit(bytes.fromhex(payment_hash_hex))  # 32 bytes -> 52 groups
    assert len(ph_groups) == 52
    timestamp = [0] * 7
    tag = [1, len(ph_groups) // 32, len(ph_groups) % 32]  # p=1, then 2-group length
    signature = [0] * 104
    checksum = [0] * 6  # decoder drops these; value is irrelevant
    groups = timestamp + tag + ph_groups + signature + checksum
    return "lnbc1" + "".join(_CHARSET[g] for g in groups)


def invoice_for_preimage(preimage_hex: str) -> str:
    """Build an invoice whose payment hash is sha256(preimage)."""
    ph = hashlib.sha256(bytes.fromhex(preimage_hex)).hexdigest()
    return make_invoice(ph)
