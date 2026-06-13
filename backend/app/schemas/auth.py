import uuid as _uuid

from pydantic import BaseModel, field_validator


class NostrAuthRequest(BaseModel):
    pubkey: str
    event: dict


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    pubkey: str

    model_config = {"from_attributes": True}

    @field_validator("id", mode="before")
    @classmethod
    def coerce_uuid(cls, v: object) -> str:
        return str(v)
