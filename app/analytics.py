import asyncio
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from .database import get_db
from .models import Log
from datetime import datetime, timedelta, timezone

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"]
)

@router.get("/")
async def get_analytics(db: AsyncSession = Depends(get_db)):
    twenty_four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=24)
    query = select(Log).where(Log.timestamp_utc >= twenty_four_hours_ago)
    subq = query.subquery()
    
    total_requests_res = await db.execute(select(func.count()).select_from(subq))
    
    successful_requests_res = await db.execute(select(func.count()).select_from(
        subq.select().where(subq.c.status_code < 400)
    ))
    
    total_requests = total_requests_res.scalar_one_or_none() or 0
    successful_requests = successful_requests_res.scalar_one_or_none() or 0
    total_errors = total_requests - successful_requests

    status_codes_query = select(
        subq.c.status_code, func.count()
    ).select_from(subq).group_by(subq.c.status_code)
    
    status_codes_res = await db.execute(status_codes_query)
    status_code_counts = {'2xx': 0, '4xx': 0, '5xx': 0}
    for code, count in status_codes_res.all():
        if 200 <= code < 300:
            status_code_counts['2xx'] += count
        elif 400 <= code < 500:
            status_code_counts['4xx'] += count
        elif 500 <= code < 600:
            status_code_counts['5xx'] += count

    requests_over_time_query = select(
        func.date_trunc('hour', subq.c.timestamp_utc).label('hour'),
        func.count().label('count')
    ).select_from(subq).group_by('hour').order_by('hour')
    requests_over_time_res = await db.execute(requests_over_time_query)
    
    top_endpoints_query = select(
        subq.c.request_path, func.count().label('count')
    ).select_from(subq).group_by(subq.c.request_path).order_by(desc('count')).limit(5)
    top_endpoints_res = await db.execute(top_endpoints_query)
    
    top_users_query = select(
        subq.c.user_id, func.count().label('count')
    ).select_from(subq).group_by(subq.c.user_id).order_by(desc('count')).limit(5)
    top_users_res = await db.execute(top_users_query)
    
    recent_errors_query = select(
        subq.c.id, subq.c.timestamp_utc, subq.c.request_path, subq.c.status_code
    ).select_from(subq).where(subq.c.status_code >= 400).order_by(desc(subq.c.timestamp_utc)).limit(10)
    recent_errors_res = await db.execute(recent_errors_query)

    requests_over_time = [
        {"hour": row.hour.strftime('%H:%M'), "count": row.count} 
        for row in requests_over_time_res.all()
    ]
        
    return {
        "total_requests": total_requests,
        "successful_requests": successful_requests,
        "total_errors": total_errors,
        "status_code_counts": status_code_counts,
        "requests_over_time": requests_over_time,
        "top_endpoints": top_endpoints_res.mappings().all(),
        "top_users": top_users_res.mappings().all(),
        "recent_errors": recent_errors_res.mappings().all()
    }