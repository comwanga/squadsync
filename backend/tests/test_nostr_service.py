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


from app.services import nostr_service


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


from coincurve import PrivateKey


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
