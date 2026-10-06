from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_session
from ..auth import current_user
from .. import models, schemas

router = APIRouter(prefix="/api/v1/crwo", tags=["crwo"])
REGIONS = ["FEO", "EVP", "KER", "SIM", "SEV", "YAL"]
RANGE_SIZE = 100


@router.post("/reserve")
async def reserve(data: schemas.ReserveIn,
                  user=Depends(current_user),
                  session: AsyncSession = Depends(get_session)):
    max_end = (await session.execute(
        select(func.coalesce(func.max(models.CrwoRange.range_end), 0))
    )).scalar()
    start = max_end + 1
    end = start + RANGE_SIZE - 1

    result = {}
    for region in REGIONS:
        existing = (await session.execute(
            select(models.CrwoRange).where(
                models.CrwoRange.device_id == data.device_id,
                models.CrwoRange.region == region,
                models.CrwoRange.current_value < models.CrwoRange.range_end,
            )
        )).scalar_one_or_none()

        if existing:
            result[region] = {"current": existing.current_value,
                              "end": existing.range_end}
            continue

        session.add(models.CrwoRange(
            device_id=data.device_id, region=region,
            range_start=start, range_end=end, current_value=start - 1,
        ))
        result[region] = {"current": start - 1, "end": end}
        start = end + 1
        end = start + RANGE_SIZE - 1

    await session.commit()
    return result


@router.post("/commit")
async def commit(data: schemas.CommitIn,
                 user=Depends(current_user),
                 session: AsyncSession = Depends(get_session)):
    existing = (await session.execute(
        select(models.CrwoCommit).where(
            models.CrwoCommit.region == data.region,
            models.CrwoCommit.value == data.value,
        )
    )).scalar_one_or_none()
    if existing:
        return {"ok": True, "duplicate": True}

    session.add(models.CrwoCommit(region=data.region, value=data.value,
                                  device_id=data.device_id))
    await session.commit()
    return {"ok": True}
