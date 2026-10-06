# backend/migrate_users.py
import sqlite3
import asyncio
from app.db import SessionLocal, init_db
from app import models


async def main():
    await init_db()
    async with SessionLocal() as session:
        con = sqlite3.connect("db.sqlite")   # закинь сюда свою старую БД
        for fn, ln, pw_hash in con.execute(
            "SELECT first_name, last_name, password_hash FROM users"
        ):
            session.add(models.User(
                first_name=fn, last_name=ln,
                password_hash=pw_hash, role="user",
            ))
        await session.commit()

        # Первого делаем админом
        from sqlalchemy import select
        users = (await session.execute(
            select(models.User).order_by(models.User.id)
        )).scalars().all()
        if users:
            users[0].role = "admin"
            await session.commit()


asyncio.run(main())
