from datetime import datetime

from pydantic import BaseModel, ConfigDict

class AuthenticatedAPIKey(BaseModel):
    user_id: str
    public_id: str
    hashed_secret: str
    is_active: bool
    expires_at: datetime | None
    requests_per_minute_limit: int

    model_config = ConfigDict(from_attributes=True)


class APIKeyCreateRequest(BaseModel):
    user_id: str

class APIKeyCreateResponse(BaseModel):
    api_key: str

