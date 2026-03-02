from datetime import datetime

from pydantic import BaseModel


class UserConfigResponse(BaseModel):
    id: int
    configKey: str
    configValue: str
    description: str | None = None
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True


class UserConfigUpdate(BaseModel):
    configValue: str


class WatchListUpdate(BaseModel):
    stockCodes: list[str]
