import hashlib

import pytest

from app.services import bolt11
from tests.lightning_helpers import invoice_for_preimage, make_invoice

# Canonical BOLT #11 test vector: "$3 for a cup of coffee". Its payment hash is
# the well-known 0001020304...0102 used throughout the spec examples.
_SPEC_INVOICE = (
    "lnbc2500u1pvjluezpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypq"
    "dq5xysxxatsyp3k7enxv4jsxqzpuaztrnwngzn3kdzw5hydlzf03qdgm2hdq27cqv3agm2aw"
    "hz5se903vruatfhq77w3ls4evs3ch9zw97j25emudupq63nyw24cg27h2rspfj9srp"
)
_SPEC_PAYMENT_HASH = "0001020304050607080900010203040506070809000102030405060708090102"


def test_payment_hash_hex_matches_spec_vector():
    assert bolt11.payment_hash_hex(_SPEC_INVOICE) == _SPEC_PAYMENT_HASH


def test_preimage_matches_true_for_correct_preimage():
    preimage = ("11" * 32)
    invoice = invoice_for_preimage(preimage)
    assert bolt11.preimage_matches(invoice, preimage) is True


def test_preimage_matches_false_for_wrong_preimage():
    invoice = invoice_for_preimage("11" * 32)
    assert bolt11.preimage_matches(invoice, "22" * 32) is False


def test_preimage_matches_false_for_unparseable_invoice():
    # A wallet returning a bogus invoice/preimage must never read as verified.
    assert bolt11.preimage_matches("not-an-invoice", "deadbeef") is False


def test_preimage_matches_false_for_non_hex_preimage():
    invoice = invoice_for_preimage("11" * 32)
    assert bolt11.preimage_matches(invoice, "preimage_lnbc210fake") is False


def test_make_invoice_roundtrips_through_decoder():
    # The helper-encoded hash is recovered by the production decoder.
    h = hashlib.sha256(b"squadsync").hexdigest()
    assert bolt11.payment_hash_hex(make_invoice(h)) == h
