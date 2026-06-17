"""Best-effort Nostr NIP-04 DM sender.

Self-contained: decodes bech32 keys, encrypts/signs a kind-4 event, and
publishes it to relays. `send_dm` never raises and no-ops when unconfigured.
Personal secret keys must never be stored — `SQUADSYNC_NSEC` is a dedicated bot key.
"""
import base64
import logging
import os

from coincurve import PrivateKey, PublicKey
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

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
