"""LNURL-pay client: resolve a `name@domain` Lightning address to a bolt11 invoice.

Two steps per LNURL spec (LUD-06/LUD-16):
  1. GET https://{domain}/.well-known/lnurlp/{name}  -> {callback, minSendable, maxSendable, ...}
  2. GET {callback}?amount={msat}                    -> {pr: <bolt11>}

All errors raise LnurlError; the caller marks that payout item failed and continues.
"""
import httpx

_TIMEOUT = 10.0


class LnurlError(Exception):
    """Any failure resolving an address or fetching an invoice."""


def lud16_to_url(address: str) -> str:
    address = address.strip().lower()
    if address.count("@") != 1:
        raise LnurlError(f"malformed lightning address: {address!r}")
    name, domain = address.split("@")
    if not name or not domain:
        raise LnurlError(f"malformed lightning address: {address!r}")
    return f"https://{domain}/.well-known/lnurlp/{name}"


def resolve_lnurl(address: str) -> dict:
    """Return the LNURL-pay params dict for a `name@domain` address."""
    url = lud16_to_url(address)
    try:
        resp = httpx.get(url, timeout=_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # noqa: BLE001 — normalize to LnurlError
        raise LnurlError(f"failed to resolve {address}: {exc}") from exc
    if "callback" not in data or "minSendable" not in data or "maxSendable" not in data:
        raise LnurlError(f"invalid LNURL-pay response for {address}")
    return data


def request_invoice(params: dict, amount_sats: int) -> str:
    """Request a bolt11 invoice for `amount_sats` from a resolved LNURL params dict."""
    amount_msat = amount_sats * 1000
    if amount_msat < params["minSendable"] or amount_msat > params["maxSendable"]:
        raise LnurlError(
            f"amount {amount_sats} sat outside payable range "
            f"[{params['minSendable'] // 1000}, {params['maxSendable'] // 1000}] sat"
        )
    try:
        resp = httpx.get(params["callback"], params={"amount": amount_msat},
                         timeout=_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # noqa: BLE001
        raise LnurlError(f"invoice request failed: {exc}") from exc
    pr = data.get("pr")
    if not pr:
        raise LnurlError("LNURL callback returned no invoice")
    return pr
