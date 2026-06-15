import asyncio
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ..database import get_db
from ..models import User, Job
from ..schemas import JobCreate, JobResponse
from ..auth import get_current_user
from ..config import settings

router = APIRouter(prefix="/jobs", tags=["jobs"])

PIPELINE_TASKS = {
    "reddit": "web.backend.tasks.generate.reddit",
    "brat": "web.backend.tasks.generate.brat",
    "montage": "web.backend.tasks.generate.montage",
    "stocks_dca": "web.backend.tasks.generate.stocks_dca",
    "stocks_compare": "web.backend.tasks.generate.stocks_compare",
    "familyguy": "web.backend.tasks.generate.familyguy",
    "movies": "web.backend.tasks.generate.movies",
}

MONTHLY_LIMITS = {"free": 5, "pro": 100, "agency": None}


async def _check_quota(user: User, db: AsyncSession):
    limit = MONTHLY_LIMITS.get(user.subscription_tier)
    if limit is None:
        return
    from datetime import datetime, timedelta
    start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.count()).where(Job.user_id == user.id, Job.created_at >= start)
    )
    count = result.scalar()
    if count >= limit:
        raise HTTPException(status_code=402, detail=f"Monthly limit of {limit} jobs reached. Upgrade your plan.")


@router.post("/", response_model=JobResponse)
async def create_job(
    body: JobCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if body.pipeline not in PIPELINE_TASKS:
        raise HTTPException(status_code=400, detail=f"Unknown pipeline: {body.pipeline}")

    await _check_quota(user, db)

    job = Job(user_id=user.id, pipeline=body.pipeline, params=body.params)
    db.add(job)
    await db.commit()
    await db.refresh(job)

    from celery import Celery
    celery_app = Celery(broker=settings.redis_url)
    task = celery_app.send_task(PIPELINE_TASKS[body.pipeline], args=[job.id, body.params])
    job.celery_task_id = task.id
    await db.commit()
    await db.refresh(job)
    return job


@router.get("/", response_model=list[JobResponse])
async def list_jobs(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Job).where(Job.user_id == user.id).order_by(Job.created_at.desc()).limit(100)
    )
    return result.scalars().all()


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Job).where(Job.id == job_id, Job.user_id == user.id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.delete("/{job_id}")
async def delete_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Job).where(Job.id == job_id, Job.user_id == user.id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    await db.delete(job)
    await db.commit()
    return {"ok": True}


@router.get("/{job_id}/logs")
async def stream_logs(
    job_id: str,
    user: User = Depends(get_current_user),
):
    import redis.asyncio as aioredis

    async def event_stream():
        r = aioredis.from_url(settings.redis_url)
        index = 0
        try:
            while True:
                lines = await r.lrange(f"job_logs:{job_id}", index, -1)
                for line in lines:
                    yield f"data: {line.decode()}\n\n"
                    index += 1
                if not lines:
                    await asyncio.sleep(1)
        finally:
            await r.aclose()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/{job_id}/upload")
async def upload_to_tiktok(
    job_id: str,
    account_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Job).where(Job.id == job_id, Job.user_id == user.id))
    job = result.scalar_one_or_none()
    if not job or job.status != "done" or not job.output_path:
        raise HTTPException(status_code=400, detail="Job not done or no output")

    from celery import Celery
    celery_app = Celery(broker=settings.redis_url)
    celery_app.send_task("web.backend.tasks.upload.tiktok", args=[job.output_path, account_id])
    return {"ok": True}
