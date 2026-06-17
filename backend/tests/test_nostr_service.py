from app.core.config import Settings


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
