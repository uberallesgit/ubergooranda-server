import json
import asyncio
from collections import defaultdict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from ..db import SessionLocal
from ..auth import decode_token
from .. import models

router = APIRouter()

connections: dict[int, set[WebSocket]] = defaultdict(set)
user_rooms: dict[int, set[int]] = defaultdict(set)
lock = asyncio.Lock()


@router.websocket("/api/v1/chat/ws")
async def chat_ws(ws: WebSocket):
    token = ws.query_params.get("token")
    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])
    except Exception:
        await ws.close(code=4001)
        return

    await ws.accept()
    async with lock:
        connections[user_id].add(ws)

    # Загружаем комнаты юзера
    async with SessionLocal() as session:
        rows = (await session.execute(
            select(models.ChatMember.room_id).where(
                models.ChatMember.user_id == user_id
            )
        )).scalars().all()
        async with lock:
            user_rooms[user_id] = set(rows)

    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)

            if msg.get("type") == "subscribe":
                async with lock:
                    user_rooms[user_id].update(msg.get("room_ids", []))
                await ws.send_json({"type": "subscribed",
                                    "room_ids": msg.get("room_ids", [])})

            elif msg.get("type") == "ping":
                await ws.send_json({"type": "pong"})

    except WebSocketDisconnect:
        pass
    finally:
        async with lock:
            connections[user_id].discard(ws)


async def _send_to_users(user_ids: set[int], payload: dict):
    dead = []
    async with lock:
        ws_by_user = {uid: list(connections.get(uid, ())) for uid in user_ids}
    for uid, wss in ws_by_user.items():
        for ws in wss:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append((uid, ws))
    async with lock:
        for uid, ws in dead:
            connections[uid].discard(ws)


async def broadcast_message(room_id: int, message: dict):
    """Отправить сообщение всем подписчикам комнаты."""
    async with lock:
        targets = {uid for uid, rooms in user_rooms.items() if room_id in rooms}
    await _send_to_users(targets, {"type": "message", "room_id": room_id, **message})


async def notify_room(room_id: int, payload: dict):
    """Служебное уведомление (создание комнаты и т.п.)."""
    # В реальности — только участникам комнаты. Для простоты шлём всем.
    async with lock:
        all_users = set(connections.keys())
    await _send_to_users(all_users, {**payload, "room_id": room_id})
