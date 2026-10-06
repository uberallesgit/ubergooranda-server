from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_session
from ..auth import current_user
from .. import models, schemas
from .chat_ws import broadcast_message, notify_room

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.get("/rooms")
async def get_rooms(user=Depends(current_user),
                    session: AsyncSession = Depends(get_session)):
    uid = int(user["sub"])
    rows = (await session.execute(
        select(models.ChatMember, models.ChatRoom)
        .join(models.ChatRoom, models.ChatMember.room_id == models.ChatRoom.id)
        .where(models.ChatMember.user_id == uid)
    )).all()

    result = []
    for member, room in rows:
        last_msg = (await session.execute(
            select(models.ChatMessage)
            .where(models.ChatMessage.room_id == room.id)
            .order_by(models.ChatMessage.id.desc())
            .limit(1)
        )).scalar_one_or_none()
        last_message_id = last_msg.id if last_msg else 0

        unread = (await session.execute(
            select(func.count()).select_from(models.ChatMessage)
            .where(
                models.ChatMessage.room_id == room.id,
                models.ChatMessage.id > member.last_read_id,
                models.ChatMessage.user_id != uid,
            )
        )).scalar() or 0

        result.append({
            "id": room.id, "kind": room.kind, "title": room.title,
            "crwo_ref": room.crwo_ref,
            "last_read_id": member.last_read_id,
            "last_message_id": last_message_id,
            "unread_count": unread,
            "muted": member.muted,
        })

    result.sort(key=lambda r: r["last_message_id"], reverse=True)
    return {"rooms": result}


@router.post("/rooms")
async def create_room(data: schemas.CreateRoomIn,
                      user=Depends(current_user),
                      session: AsyncSession = Depends(get_session)):
    uid = int(user["sub"])
    room = models.ChatRoom(
        kind=data.kind, title=data.title,
        crwo_ref=data.crwo_ref, created_by=uid,
    )
    session.add(room)
    await session.flush()

    member_ids = set(data.member_ids) | {uid}
    for mid in member_ids:
        session.add(models.ChatMember(room_id=room.id, user_id=mid))

    await session.commit()

    # Уведомляем всех участников через WS, чтобы у них комната появилась
    await notify_room(room.id, {
        "type": "room_created",
        "room_id": room.id, "title": room.title,
        "kind": room.kind,
    })

    return {"id": room.id}


@router.get("/rooms/{room_id}/messages")
async def get_messages(
    room_id: int,
    since: int = 0,
    before: int = 0,
    limit: int = 50,
    user=Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    uid = int(user["sub"])
    member = (await session.execute(
        select(models.ChatMember).where(
            models.ChatMember.room_id == room_id,
            models.ChatMember.user_id == uid,
        )
    )).scalar_one_or_none()
    if not member:
        raise HTTPException(403, "not a member")

    query = select(models.ChatMessage).where(models.ChatMessage.room_id == room_id)
    if since > 0:
        query = query.where(models.ChatMessage.id > since) \
                     .order_by(models.ChatMessage.id.asc()).limit(limit)
    elif before > 0:
        query = query.where(models.ChatMessage.id < before) \
                     .order_by(models.ChatMessage.id.desc()).limit(limit)
    else:
        query = query.order_by(models.ChatMessage.id.desc()).limit(limit)

    rows = (await session.execute(query)).scalars().all()

    messages = []
    for m in rows:
        author = await session.get(models.User, m.user_id)
        messages.append({
            "id": m.id, "room_id": m.room_id, "user_id": m.user_id,
            "author_name": author.first_name if author else "?",
            "body": m.body, "attachment_url": m.attachment_url,
            "created_at": m.created_at.isoformat(),
        })

    max_id = max((m["id"] for m in messages), default=since)
    return {"messages": messages, "max_id": max_id}


@router.post("/rooms/{room_id}/messages")
async def send_message(room_id: int, data: schemas.SendMessageIn,
                       user=Depends(current_user),
                       session: AsyncSession = Depends(get_session)):
    uid = int(user["sub"])
    member = (await session.execute(
        select(models.ChatMember).where(
            models.ChatMember.room_id == room_id,
            models.ChatMember.user_id == uid,
        )
    )).scalar_one_or_none()
    if not member:
        raise HTTPException(403, "not a member")

    msg = models.ChatMessage(
        room_id=room_id, user_id=uid,
        body=data.body, attachment_url=data.attachment_url,
    )
    session.add(msg)
    await session.commit()
    await session.refresh(msg)

    author = await session.get(models.User, uid)
    payload = {
        "id": msg.id, "room_id": room_id, "user_id": uid,
        "author_name": author.first_name if author else "?",
        "body": msg.body, "attachment_url": msg.attachment_url,
        "created_at": msg.created_at.isoformat(),
    }

    # Отправляем всем участникам через WebSocket
    await broadcast_message(room_id, payload)
    return payload


@router.post("/rooms/{room_id}/read")
async def mark_read(room_id: int, data: schemas.ReadIn,
                    user=Depends(current_user),
                    session: AsyncSession = Depends(get_session)):
    uid = int(user["sub"])
    await session.execute(
        update(models.ChatMember)
        .where(models.ChatMember.room_id == room_id,
               models.ChatMember.user_id == uid,
               models.ChatMember.last_read_id < data.last_read_id)
        .values(last_read_id=data.last_read_id)
    )
    await session.commit()
    return {"ok": True}
