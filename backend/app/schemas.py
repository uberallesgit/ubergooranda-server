from pydantic import BaseModel
from typing import Optional


class RegisterIn(BaseModel):
    first_name: str
    last_name: str
    password: str


class LoginIn(BaseModel):
    first_name: str
    last_name: str
    password: str

class CrwoCheckIn(BaseModel):
    region: str
    value: int


class CrwoCommitIn(BaseModel):
    region: str
    value: int
    device_id: str
    forced: bool = False

class ReadIn(BaseModel):
    last_read_id: int


class CreateRoomIn(BaseModel):
    kind: str
    title: str
    member_ids: list[int]
    crwo_ref: Optional[str] = None


class SendMessageIn(BaseModel):
    body: str
    attachment_url: Optional[str] = None
