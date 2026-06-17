import json
import pytest
from coincurve import PrivateKey

from app.services import nwc_service
from app.services.nwc_service import NwcError, parse_nwc_uri, build_pay_invoice_request, decode_response
from app.services.nostr_service import encrypt_nip04


def _make_uri(secret_hex: str, wallet_pub_hex: str, relay="wss://relay.example") -> str:
    return f"nostr+walletconnect://{wallet_pub_hex}?relay={relay}&secret={secret_hex}"


def test_parse_nwc_uri():
    secret = PrivateKey()
    wallet = PrivateKey()
    wallet_xonly = wallet.public_key_xonly.format().hex()
    uri = _make_uri(secret.to_hex(), wallet_xonly)
    parsed = parse_nwc_uri(uri)
    assert parsed.wallet_pubkey_hex == wallet_xonly
    assert parsed.relay == "wss://relay.example"
    assert parsed.secret_bytes == secret.secret


def test_parse_nwc_uri_rejects_garbage():
    with pytest.raises(NwcError):
        parse_nwc_uri("https://not-nwc")


def test_build_pay_invoice_request_is_signed_and_encrypted():
    secret = PrivateKey()
    wallet = PrivateKey()
    wallet_xonly = wallet.public_key_xonly.format().hex()
    event = build_pay_invoice_request(secret.secret, bytes.fromhex(wallet_xonly), "lnbc1fake")
    assert event["kind"] == 23194
    assert ["p", wallet_xonly] in event["tags"]
    # wallet decrypts the request with its privkey + our x-only pubkey
    our_xonly = secret.public_key_xonly.format()
    from app.services.nostr_service import decrypt_nip04
    body = json.loads(decrypt_nip04(wallet.secret, our_xonly, event["content"]))
    assert body["method"] == "pay_invoice"
    assert body["params"]["invoice"] == "lnbc1fake"


def test_decode_response_success():
    secret = PrivateKey()
    wallet = PrivateKey()
    our_xonly = secret.public_key_xonly.format()
    payload = json.dumps({"result_type": "pay_invoice", "result": {"preimage": "deadbeef"}})
    content = encrypt_nip04(wallet.secret, our_xonly, payload)
    result = decode_response(secret.secret, wallet.public_key_xonly.format(), content)
    assert result == {"preimage": "deadbeef"}


def test_decode_response_error_raises():
    secret = PrivateKey()
    wallet = PrivateKey()
    our_xonly = secret.public_key_xonly.format()
    payload = json.dumps({"error": {"code": "INSUFFICIENT_BALANCE", "message": "no funds"}})
    content = encrypt_nip04(wallet.secret, our_xonly, payload)
    with pytest.raises(NwcError) as exc:
        decode_response(secret.secret, wallet.public_key_xonly.format(), content)
    assert "no funds" in str(exc.value)
