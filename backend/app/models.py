from datetime import datetime
from pydantic import BaseModel, Field


class RoomState(BaseModel):
    light_on: bool = False
    shutter_open: bool = False
    temperature: float | None = None
    fire_state: str = "NORMAL"
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TemperaturePoint(BaseModel):
    room: str
    value: float
    measured_at: datetime


class ToggleResponse(BaseModel):
    room: str
    ok: bool
    command: str


class FireTestRequest(BaseModel):
    source: str = "ui"


class RoomsStateResponse(BaseModel):
    rooms: dict[str, RoomState]
