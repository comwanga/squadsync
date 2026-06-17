"""Best-effort Nostr NIP-04 DM sender.

Self-contained: decodes bech32 keys, encrypts/signs a kind-4 event, and
publishes it to relays. `send_dm` never raises and no-ops when unconfigured.
Personal secret keys must never be stored — `SQUADSYNC_NSEC` is a dedicated bot key.
"""
import logging

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
    return hrp, bytes(out)
