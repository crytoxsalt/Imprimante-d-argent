from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ..database import get_db
from ..models import User, Job
from ..auth import get_current_user
from ..schemas import AnalyticsSummary

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
async def summary(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Total jobs
    total_result = await db.execute(
        select(func.count()).where(Job.user_id == user.id)
    )
    total = total_result.scalar()

    # Jobs by pipeline
    pipeline_result = await db.execute(
        select(Job.pipeline, func.count()).where(Job.user_id == user.id).group_by(Job.pipeline)
    )
    by_pipeline = {row[0]: row[1] for row in pipeline_result}

    # Jobs per day last 30 days
    since = datetime.utcnow() - timedelta(days=30)
    daily_result = await db.execute(
        select(
            func.date(Job.created_at).label("day"),
            func.count().label("count"),
        )
        .where(Job.user_id == user.id, Job.created_at >= since)
        .group_by(func.date(Job.created_at))
        .order_by(func.date(Job.created_at))
    )
    daily = [{"day": str(row.day), "count": row.count} for row in daily_result]

    # Success rate
    done_result = await db.execute(
        select(func.count()).where(Job.user_id == user.id, Job.status == "done")
    )
    done = done_result.scalar()
    rate = (done / total) if total > 0 else 0.0

    return AnalyticsSummary(
        total_jobs=total,
        jobs_by_pipeline=by_pipeline,
        jobs_last_30_days=daily,
        success_rate=rate,
    )
