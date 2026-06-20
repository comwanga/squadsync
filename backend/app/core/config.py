from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    # Allowed CORS origin(s) for the browser frontend. Accepts a single origin
    # or a comma-separated list (e.g. the Render/Vercel URL plus a custom domain).
    # Trailing slashes are stripped — the CORS spec matches origins exactly, and a
    # stray slash is a common cause of "No 'Access-Control-Allow-Origin'" failures.
    FRONTEND_URL: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.FRONTEND_URL.split(",") if o.strip()]
    # Canonical public base URL of this API (e.g. https://squadsync-api.onrender.com).
    # Used to bind NIP-98 auth events behind a TLS-terminating proxy, where the
    # request URL FastAPI sees (http, internal host) differs from the signed URL.
    # When unset, the live request URL is used (correct for local/dev).
    PUBLIC_API_URL: str | None = None
    # Hard ceiling on a single team payout (sats). A safety net against a
    # fat-finger (extra zeros) — the request is refused before anything is sent.
    PAYOUT_MAX_SATS: int = 5_000_000
    # Optional: enables AI normalization of free-text "Other" strengths.
    # When unset, allocation falls back to a deterministic slug per Other entry.
    ANTHROPIC_API_KEY: str | None = None
    CATEGORIZATION_MODEL: str = "claude-haiku-4-5-20251001"

    # --- Nostr DM sender (all optional; unset → DM sending is a no-op) ---
    # Dedicated *bot* secret key (bech32 `nsec1…`) used ONLY to sign/encrypt
    # outgoing DMs. NEVER put a personal nsec here. When unset, send_dm no-ops.
    SQUADSYNC_NSEC: str | None = None
    # Recipient for the Settings feedback box (bech32 `npub1…`, the owner's public key).
    FEEDBACK_NPUB: str | None = None
    # Comma-separated relay websocket URLs to publish DMs to.
    NOSTR_RELAYS: str = "wss://relay.damus.io,wss://nos.lol,wss://relay.nostr.band"

    @property
    def nostr_relays(self) -> list[str]:
        return [r.strip() for r in self.NOSTR_RELAYS.split(",") if r.strip()]

    class Config:
        env_file = ".env"


settings = Settings()
