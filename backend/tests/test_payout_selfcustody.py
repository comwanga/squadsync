"""Self-custody payout contract: the server creates pending items and verifies
reported preimages, but never receives the NWC spend credential (the browser
does the NIP-47 send). See docs/superpowers/specs/2026-06-20-self-custody-payouts-design.md.
"""
import hashlib

from tests.test_payout_endpoint import _setup_team
from tests.lightning_helpers import invoice_for_preimage


def _report_result(client, headers, payout_id, item_id, preimage):
    invoice = invoice_for_preimage(preimage)
    return client.post(
        f"/api/v1/allocations/payouts/{payout_id}/items/{item_id}/result",
        headers=headers, json={"bolt11": invoice, "preimage": preimage},
    )


def test_create_without_nwc_returns_pending_and_sends_nothing(client, auth_headers):
    _, allocation_id, team_id, members = _setup_team(client, auth_headers, all_have_addresses=True)
    res = client.post(f"/api/v1/allocations/{allocation_id}/payouts", headers=auth_headers, json={
        "team_id": str(team_id), "total_sats": 210,  # no nwc -> self-custody path
    })
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["status"] == "pending"
    assert len(body["items"]) == len(members)
    assert all(i["status"] == "pending" and i["preimage"] is None for i in body["items"])
    assert sum(i["amount_sats"] for i in body["items"]) == 210


def test_reporting_valid_preimages_marks_paid_and_completes(client, auth_headers):
    _, allocation_id, team_id, members = _setup_team(client, auth_headers, all_have_addresses=True)
    payout = client.post(f"/api/v1/allocations/{allocation_id}/payouts", headers=auth_headers,
                         json={"team_id": str(team_id), "total_sats": 210}).json()

    final = None
    for item in payout["items"]:
        preimage = hashlib.sha256(item["id"].encode()).hexdigest()
        res = _report_result(client, auth_headers, payout["id"], item["id"], preimage)
        assert res.status_code == 200, res.text
        final = res.json()

    assert final["status"] == "complete"
    assert all(i["status"] == "paid" and i["preimage"] for i in final["items"])


def test_reporting_mismatched_preimage_is_unverified(client, auth_headers):
    _, allocation_id, team_id, _ = _setup_team(client, auth_headers, all_have_addresses=True)
    payout = client.post(f"/api/v1/allocations/{allocation_id}/payouts", headers=auth_headers,
                         json={"team_id": str(team_id), "total_sats": 210}).json()
    item = payout["items"][0]
    # bolt11 commits to one payment hash; report a preimage for a different one.
    res = client.post(
        f"/api/v1/allocations/payouts/{payout['id']}/items/{item['id']}/result",
        headers=auth_headers,
        json={"bolt11": invoice_for_preimage("11" * 32), "preimage": "22" * 32},
    )
    assert res.status_code == 200, res.text
    reported = next(i for i in res.json()["items"] if i["id"] == item["id"])
    assert reported["status"] == "unverified"


def test_reporting_failure_marks_item_failed(client, auth_headers):
    _, allocation_id, team_id, _ = _setup_team(client, auth_headers, all_have_addresses=True)
    payout = client.post(f"/api/v1/allocations/{allocation_id}/payouts", headers=auth_headers,
                         json={"team_id": str(team_id), "total_sats": 210}).json()
    item = payout["items"][0]
    res = client.post(
        f"/api/v1/allocations/payouts/{payout['id']}/items/{item['id']}/failed",
        headers=auth_headers, json={"error": "wallet declined"},
    )
    assert res.status_code == 200, res.text
    reported = next(i for i in res.json()["items"] if i["id"] == item["id"])
    assert reported["status"] == "failed"
    assert reported["error"] == "wallet declined"


def test_reporting_result_is_idempotent_on_paid_item(client, auth_headers):
    _, allocation_id, team_id, _ = _setup_team(client, auth_headers, all_have_addresses=True)
    payout = client.post(f"/api/v1/allocations/{allocation_id}/payouts", headers=auth_headers,
                         json={"team_id": str(team_id), "total_sats": 210}).json()
    item = payout["items"][0]
    preimage = hashlib.sha256(item["id"].encode()).hexdigest()
    first = _report_result(client, auth_headers, payout["id"], item["id"], preimage).json()
    paid_preimage = next(i for i in first["items"] if i["id"] == item["id"])["preimage"]

    # A duplicate report (client retry) must not change or re-count the paid item.
    second = _report_result(client, auth_headers, payout["id"], item["id"], preimage).json()
    again = next(i for i in second["items"] if i["id"] == item["id"])
    assert again["status"] == "paid"
    assert again["preimage"] == paid_preimage


def test_result_endpoint_requires_organizer(client, auth_headers, nostr_privkey):
    _, allocation_id, team_id, _ = _setup_team(client, auth_headers, all_have_addresses=True)
    payout = client.post(f"/api/v1/allocations/{allocation_id}/payouts", headers=auth_headers,
                         json={"team_id": str(team_id), "total_sats": 210}).json()
    item = payout["items"][0]

    # A different authenticated user (not the organizer) is rejected.
    from tests.conftest import make_nostr_event
    from coincurve import PrivateKey
    other = PrivateKey()
    pubkey = other.public_key.format(compressed=True)[1:].hex()
    token = client.post("/auth/nostr", json={
        "pubkey": pubkey, "event": make_nostr_event(other),
    }).json()["access_token"]

    res = client.post(
        f"/api/v1/allocations/payouts/{payout['id']}/items/{item['id']}/result",
        headers={"Authorization": f"Bearer {token}"},
        json={"bolt11": invoice_for_preimage("11" * 32), "preimage": "11" * 32},
    )
    assert res.status_code in (401, 403, 404)
