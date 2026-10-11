# backend/app/routers/crwo.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_session
from ..auth import current_user
from .. import models, schemas

router = APIRouter(prefix="/api/v1/crwo", tags=["crwo"])

REGIONS = ["FEO", "EVP", "KER", "SIM", "SEV", "YAL"]


@router.post("/check")
async def check(
    data: schemas.CrwoCheckIn,
    user=Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    if data.region not in REGIONS:
        raise HTTPException(400, f"Неверный регион: {data.region}")

    existing = (await session.execute(
        select(models.CrwoCommit)
        .where(
            models.CrwoCommit.region == data.region,
            models.CrwoCommit.value == data.value,
            models.CrwoCommit.forced == False,
        )
        .order_by(models.CrwoCommit.committed_at.asc())
        .limit(1)
    )).scalar_one_or_none()

    if not existing:
        return {"status": "free"}

    max_used = (await session.execute(
        select(func.coalesce(func.max(models.CrwoCommit.value), 0))
        .where(models.CrwoCommit.region == data.region)
    )).scalar() or 0

    next_free = max_used + 1

    used_by_user = None
    if existing.user_id:
        u = await session.get(models.User, existing.user_id)
        if u:
            used_by_user = f"{u.last_name} {u.first_name}".strip()

    return {
        "status": "taken",
        "used_by": used_by_user or "неизвестно",
        "used_at": existing.committed_at.isoformat() if existing.committed_at else None,
        "next_free": next_free,
    }


@router.post("/commit")
async def commit(
    data: schemas.CrwoCommitIn,
    user=Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    if data.region not in REGIONS:
        raise HTTPException(400, f"Неверный регион: {data.region}")

    uid = int(user["sub"])

    if not data.forced:
        existing = (await session.execute(
            select(models.CrwoCommit)
            .where(
                models.CrwoCommit.region == data.region,
                models.CrwoCommit.value == data.value,
                models.CrwoCommit.forced == False,
            )
        )).scalar_one_or_none()

        if existing:
            raise HTTPException(409, "Номер уже использован")

    commit_row = models.CrwoCommit(
        region=data.region,
        value=data.value,
        user_id=uid,
        device_id=data.device_id,
        forced=data.forced,
    )
    session.add(commit_row)
    await session.commit()
    await session.refresh(commit_row)

    return {"ok": True, "id": commit_row.id}
