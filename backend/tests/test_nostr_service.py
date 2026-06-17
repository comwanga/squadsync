import hashlib
import json

from coincurve import PrivateKey, PublicKeyXOnly

from app.core.config import Settings
from app.services import nostr_service


def test_nostr_relays_defaults_split_on_comma():
    s = Settings(DATABASE_URL="sqlite://", SECRET_KEY="x")
    assert s.nostr_relays == [
        "wss://relay.damus.io",
        "wss://nos.lol",
        "wss://relay.nostr.band",
    ]


def test_nostr_relays_override_and_strip():
    s = Settings(DATABASE_URL="sqlite://", SECRET_KEY="x", NOSTR_RELAYS=" wss://a , wss://b ")
    assert s.nostr_relays == ["wss://a", "wss://b"]


def test_nostr_keys_default_unset():
    s = Settings(DATABASE_URL="sqlite://", SECRET_KEY="x")
    assert s.SQUADSYNC_NSEC is None
    assert s.FEEDBACK_NPUB is None


def test_bech32_decode_npub_vector():
    hrp, key = nostr_service.bech32_decode(
        "npub180cvv07tjdrrgpa0j7j7tmnyl2yr6yr7l8j4s3evf6u64th6gkwsyjh6w6"
    )
    assert hrp == "npub"
    assert key.hex() == "3bf0c63fcb93463407af97a5e5ee64fa883d107ef9e558472c4eb9aaaefa459d"


def test_bech32_decode_nsec_vector():
    hrp, key = nostr_service.bech32_decode(
        "nsec1vl029mgpspedva04g90vltkh6fvh240zqtv9k0t9af8935ke9laqsnlfe9"
    )
    assert hrp == "nsec"
    assert key.hex() == "67dea2ed018072d675f5415ecfaed7d2597555e202d85b3d65ea4e58d2d92ffa"


def test_nip04_encrypt_decrypt_round_trip():
    bot = PrivateKey()
    recipient = PrivateKey()
    recipient_xonly = recipient.public_key_xonly.format()
    bot_xonly = bot.public_key_xonly.format()

    message = "Hello from SquadSync — café ☕"
    content = nostr_service.encrypt_nip04(bot.secret, recipient_xonly, message)
    assert "?iv=" in content

    # Recipient decrypts with their privkey + the bot's x-only pubkey.
    recovered = nostr_service.decrypt_nip04(recipient.secret, bot_xonly, content)
    assert recovered == message


def test_build_signed_event_has_valid_id_and_sig():
    bot = PrivateKey()
    recipient = PrivateKey()
    recipient_xonly = recipient.public_key_xonly.format()

    event = nostr_service.build_dm_event(bot.secret, recipient_xonly, "hi there")

    assert event["kind"] == 4
    assert event["tags"] == [["p", recipient_xonly.hex()]]
    assert event["pubkey"] == bot.public_key_xonly.format().hex()

    # id == sha256 of NIP-01 serialization
    serialized = json.dumps(
        [0, event["pubkey"], event["created_at"], event["kind"], event["tags"], event["content"]],
        separators=(",", ":"),
        ensure_ascii=False,
    )
    assert event["id"] == hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    # sig verifies against the bot's x-only pubkey over the id bytes
    assert PublicKeyXOnly(bot.public_key_xonly.format()).verify(
        bytes.fromhex(event["sig"]), bytes.fromhex(event["id"])
    )


def test_send_dm_noop_when_unconfigured(monkeypatch):
    monkeypatch.setattr(nostr_service.settings, "SQUADSYNC_NSEC", None, raising=False)
    # Must return False and NOT raise, even with a bad recipient.
    assert nostr_service.send_dm("npub-not-real", "hi") is False


def test_send_dm_returns_true_when_a_relay_accepts(monkeypatch):
    # Configure a valid bot key (the NIP-19 nsec test vector).
    monkeypatch.setattr(
        nostr_service.settings,
        "SQUADSYNC_NSEC",
        "nsec1vl029mgpspedva04g90vltkh6fvh240zqtv9k0t9af8935ke9laqsnlfe9",
        raising=False,
    )
    monkeypatch.setattr(nostr_service.settings, "NOSTR_RELAYS", "wss://relay.test", raising=False)

    published = {}

    def fake_publish(event, relays):
        published["event"] = event
        published["relays"] = relays
        return True

    monkeypatch.setattr(nostr_service, "_publish_to_relays", fake_publish)

    recipient = "npub180cvv07tjdrrgpa0j7j7tmnyl2yr6yr7l8j4s3evf6u64th6gkwsyjh6w6"
    assert nostr_service.send_dm(recipient, "hello") is True
    assert published["event"]["kind"] == 4
    assert published["relays"] == ["wss://relay.test"]


def test_send_dm_swallows_publish_errors(monkeypatch):
    monkeypatch.setattr(
        nostr_service.settings,
        "SQUADSYNC_NSEC",
        "nsec1vl029mgpspedva04g90vltkh6fvh240zqtv9k0t9af8935ke9laqsnlfe9",
        raising=False,
    )

    def boom(event, relays):
        raise RuntimeError("relay down")

    monkeypatch.setattr(nostr_service, "_publish_to_relays", boom)
    recipient = "npub180cvv07tjdrrgpa0j7j7tmnyl2yr6yr7l8j4s3evf6u64th6gkwsyjh6w6"
    # Never propagates — returns False.
    assert nostr_service.send_dm(recipient, "hello") is False
