from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_session
from .. import models, schemas
from ..auth import pwd, make_token, current_user

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register")
async def register(data: schemas.RegisterIn,
                   session: AsyncSession = Depends(get_session)):
    count = (await session.execute(
        select(func.count()).select_from(models.User)
    )).scalar()
    role = "admin" if count == 0 else "user"

    user = models.User(
        first_name=data.first_name.strip(),
        last_name=data.last_name.strip(),
        password_hash=pwd.hash(data.password),
        role=role,
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(400, "Такой пользователь уже есть")
    return {"ok": True, "role": role}


@router.post("/login")
async def login(data: schemas.LoginIn,
                session: AsyncSession = Depends(get_session)):
    user = (await session.execute(
        select(models.User).where(
            models.User.first_name == data.first_name.strip(),
            models.User.last_name == data.last_name.strip(),
        )
    )).scalar_one_or_none()

    if not user or not pwd.verify(data.password, user.password_hash):
        raise HTTPException(401, "Неверные данные")

    return {"token": make_token(user.id, user.role), "role": user.role,
            "user_id": user.id, "first_name": user.first_name, "last_name": user.last_name}


@router.get("/me")
async def me(user=Depends(current_user),
             session: AsyncSession = Depends(get_session)):
    u = await session.get(models.User, int(user["sub"]))
    if not u:
        raise HTTPException(404, "not found")
    return {"id": u.id, "first_name": u.first_name,
            "last_name": u.last_name, "role": u.role}


@router.get("/users")
async def list_users(user=Depends(current_user),
                     session: AsyncSession = Depends(get_session)):
    """Список всех пользователей — для выбора участников чата."""
    rows = (await session.execute(select(models.User))).scalars().all()
    return [{"id": u.id, "first_name": u.first_name,
             "last_name": u.last_name, "role": u.role} for u in rows]
