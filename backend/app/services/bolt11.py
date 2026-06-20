"""Minimal bolt11 reader: extract the payment hash and verify a preimage.

We never claim a Lightning payout item is "paid" on a wallet's say-so. NIP-47
returns a payment preimage; the cryptographic proof of settlement is that
`sha256(preimage) == payment_hash` of the invoice *we* asked the wallet to pay.

This decoder reads only the payment-hash tagged field (BOLT #11 type `p`). It
does NOT validate the bech32 checksum or the signature: we constructed the pay
request around this exact invoice string, so the property we need is solely
"does the returned preimage hash to this invoice's payment hash".
"""
import hashlib

_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
_TIMESTAMP_GROUPS = 7      # 35-bit timestamp prefix
_SIG_GROUPS = 104          # trailing 65-byte recoverable signature (520 bits)
_CHECKSUM_GROUPS = 6       # bech32 tail
_PAYMENT_HASH_TAG = 1      # tagged field `p`


class Bolt11Error(Exception):
    """The invoice could not be parsed far enough to read its payment hash."""


def _data_groups(invoice: str) -> list[int]:
    """5-bit data groups between the `1` separator and the bech32 checksum."""
    inv = invoice.strip().lower()
    pos = inv.rfind("1")  # data part uses no '1'; last '1' is the hrp separator
    if pos < 1:
        raise Bolt11Error("missing bech32 separator")
    try:
        groups = [_CHARSET.index(c) for c in inv[pos + 1:]]
    except ValueError as exc:
        raise Bolt11Error("invalid bech32 character") from exc
    if len(groups) < _TIMESTAMP_GROUPS + _SIG_GROUPS + _CHECKSUM_GROUPS:
        raise Bolt11Error("invoice too short")
    return groups[:-_CHECKSUM_GROUPS]


def _groups_to_bytes(groups: list[int]) -> bytes:
    acc = bits = 0
    out = bytearray()
    for v in groups:
        acc = (acc << 5) | v
        bits += 5
        while bits >= 8:
            bits -= 8
            out.append((acc >> bits) & 0xFF)
    return bytes(out)


def payment_hash_hex(invoice: str) -> str:
    """Return the 32-byte payment hash (hex) from a bolt11 invoice, or raise Bolt11Error."""
    groups = _data_groups(invoice)
    tagged = groups[_TIMESTAMP_GROUPS:-_SIG_GROUPS]
    i = 0
    while i + 3 <= len(tagged):
        typ = tagged[i]
        length = tagged[i + 1] * 32 + tagged[i + 2]
        i += 3
        field = tagged[i:i + length]
        i += length
        if typ == _PAYMENT_HASH_TAG:
            h = _groups_to_bytes(field)[:32]
            if len(h) != 32:
                raise Bolt11Error("payment hash field is not 32 bytes")
            return h.hex()
    raise Bolt11Error("no payment hash field in invoice")


def preimage_matches(invoice: str, preimage_hex: str) -> bool:
    """True iff sha256(preimage) equals the invoice's payment hash.

    Returns False (never raises) for any malformed input — an unverifiable
    preimage must read as not-proven, not as an error to be retried.
    """
    try:
        expected = payment_hash_hex(invoice)
        preimage = bytes.fromhex(preimage_hex.strip())
    except (Bolt11Error, ValueError, AttributeError):
        return False
    return hashlib.sha256(preimage).hexdigest() == expected
