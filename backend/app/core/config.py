from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    FRONTEND_URL: str = "http://localhost:3000"
    # Canonical public base URL of this API (e.g. https://squadsync-api.onrender.com).
    # Used to bind NIP-98 auth events behind a TLS-terminating proxy, where the
    # request URL FastAPI sees (http, internal host) differs from the signed URL.
    # When unset, the live request URL is used (correct for local/dev).
    PUBLIC_API_URL: str | None = None

    class Config:
        env_file = ".env"


settings = Settings()
