from sqlalchemy import (
    Column, BigInteger, String, Text, Boolean, TIMESTAMP,
    ForeignKey, Integer, func,
)
from sqlalchemy.orm import relationship
from .db import Base


class User(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="user")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class CrwoRange(Base):
    __tablename__ = "crwo_ranges"
    id = Column(BigInteger, primary_key=True)
    device_id = Column(String, nullable=False)
    region = Column(String, nullable=False)
    range_start = Column(Integer, nullable=False)
    range_end = Column(Integer, nullable=False)
    current_value = Column(Integer, nullable=False)
    issued_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class CrwoCommit(Base):
    __tablename__ = "crwo_commits"
    id = Column(BigInteger, primary_key=True)
    region = Column(String, nullable=False)
    value = Column(Integer, nullable=False)
    device_id = Column(String)
    committed_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class ChatRoom(Base):
    __tablename__ = "chat_rooms"
    id = Column(BigInteger, primary_key=True)
    kind = Column(String, nullable=False)       # 'channel' | 'direct' | 'crwo'
    title = Column(String, nullable=False)
    crwo_ref = Column(String)
    created_by = Column(BigInteger, ForeignKey("users.id"))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class ChatMember(Base):
    __tablename__ = "chat_members"
    room_id = Column(BigInteger, ForeignKey("chat_rooms.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    joined_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    last_read_id = Column(BigInteger, default=0)
    muted = Column(Boolean, default=False)


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(BigInteger, primary_key=True)
    room_id = Column(BigInteger, ForeignKey("chat_rooms.id", ondelete="CASCADE"))
    user_id = Column(BigInteger, ForeignKey("users.id"))
    body = Column(Text, nullable=False)
    attachment_url = Column(String)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
