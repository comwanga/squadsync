import pytest
from app.services import lnurl_service
from app.services.lnurl_service import LnurlError, lud16_to_url


def test_lud16_to_url():
    assert lud16_to_url("ada@getalby.com") == "https://getalby.com/.well-known/lnurlp/ada"


def test_lud16_to_url_rejects_malformed():
    with pytest.raises(LnurlError):
        lud16_to_url("not-an-address")


def test_request_invoice_amount_below_min_raises(monkeypatch):
    params = {"callback": "https://getalby.com/lnurlp/ada/callback",
              "minSendable": 100_000, "maxSendable": 1_000_000}  # 100..1000 sat

    def fake_get(url, **kwargs):
        raise AssertionError("callback should not be hit when amount is out of bounds")

    monkeypatch.setattr(lnurl_service.httpx, "get", fake_get)
    with pytest.raises(LnurlError):
        lnurl_service.request_invoice(params, amount_sats=50)  # 50 sat < 100 sat min


def test_request_invoice_returns_bolt11(monkeypatch):
    params = {"callback": "https://getalby.com/lnurlp/ada/callback",
              "minSendable": 1_000, "maxSendable": 1_000_000}

    class FakeResp:
        def raise_for_status(self): pass
        def json(self): return {"pr": "lnbc100n1fakeinvoice"}

    captured = {}

    def fake_get(url, params=None, **kwargs):
        captured["url"] = url
        captured["params"] = params
        return FakeResp()

    monkeypatch.setattr(lnurl_service.httpx, "get", fake_get)
    bolt11 = lnurl_service.request_invoice(params, amount_sats=100)
    assert bolt11 == "lnbc100n1fakeinvoice"
    assert captured["params"]["amount"] == 100_000  # msat
