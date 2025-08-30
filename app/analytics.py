from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from pydantic import BaseModel, Field
from datetime import datetime, timedelta, timezone

from .database import get_db
from .models import Logs

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"]
)

class AnalyticsResponse(BaseModel):
    total_requests: int = Field(..., description="Total number of requests logged.")
    successful_requests: int = Field(..., description="Number of requests with a 2xx status code.")
    failed_requests: int = Field(..., description="Number of requests with a 4xx or 5xx status code.")
    success_rate: float = Field(..., description="Success rate as a percentage.")
    average_latency_ms: float = Field(..., description="Average request latency in milliseconds.")

@router.get("/", response_model=AnalyticsResponse)
async def get_analytics_summary(db: AsyncSession = Depends(get_db)):
    # Define the time window
    time_window = datetime.now(timezone.utc) - timedelta(hours=24)

    # Build the base query
    query = select(
        func.count(Logs.id).label("total_requests"),
        func.sum(
            func.casewhen((Logs.status_code >= 200, Logs.status_code < 300), 1, else_=0)
        ).label("successful_requests"),
        func.avg(Logs.latency_ms).label("average_latency")
    ).where(Logs.created_at >= time_window)

    result = await db.execute(query)
    stats = result.first()

    if not stats or stats.total_requests == 0:
        return AnalyticsResponse(
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            success_rate=100.0,
            average_latency_ms=0.0
        )

    total = stats.total_requests or 0
    successful = stats.successful_requests or 0
    failed = total - successful
    success_rate = (successful / total) * 100 if total > 0 else 100.0
    avg_latency = stats.average_latency or 0.0

    return AnalyticsResponse(
        total_requests=total,
        successful_requests=successful,
        failed_requests=failed,
        success_rate=round(success_rate, 2),
        average_latency_ms=round(avg_latency, 2)
    )