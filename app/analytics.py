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

    # --- KPI Calculations (Run sequentially, not in parallel) ---
    total_requests_res = await db.execute(select(func.count(Log.id)).select_from(query.subquery()))
    successful_requests_res = await db.execute(select(func.count(Log.id)).select_from(
        query.where(Log.status_code < 400).subquery()
    ))
    
    total_requests = total_requests_res.scalar_one_or_none() or 0
    successful_requests = successful_requests_res.scalar_one_or_none() or 0
    total_errors = total_requests - successful_requests

    # --- Status Code Breakdown ---
    status_codes_query = select(
        Log.status_code, func.count(Log.id)
    ).select_from(query.subquery()).group_by(Log.status_code)
    
    status_codes_res = await db.execute(status_codes_query)
    status_code_counts = {'2xx': 0, '4xx': 0, '5xx': 0}
    for code, count in status_codes_res.all():
        if 200 <= code < 300:
            status_code_counts['2xx'] += count
        elif 400 <= code < 500:
            status_code_counts['4xx'] += count
        elif 500 <= code < 600:
            status_code_counts['5xx'] += count

    # --- Other Queries (Run sequentially) ---
    requests_over_time_query = select(
        func.date_trunc('hour', Log.timestamp_utc).label('hour'),
        func.count(Log.id).label('count')
    ).select_from(query.subquery()).group_by('hour').order_by('hour')
    requests_over_time_res = await db.execute(requests_over_time_query)
    
    top_endpoints_query = select(
        Log.request_path, func.count(Log.id).label('count')
    ).select_from(query.subquery()).group_by(Log.request_path).order_by(desc('count')).limit(5)
    top_endpoints_res = await db.execute(top_endpoints_query)
    
    top_users_query = select(
        Log.user_id, func.count(Log.id).label('count')
    ).select_from(query.subquery()).group_by(Log.user_id).order_by(desc('count')).limit(5)
    top_users_res = await db.execute(top_users_query)
    
    recent_errors_query = select(
        Log.id, Log.timestamp_utc, Log.request_path, Log.status_code
    ).select_from(query.where(Log.status_code >= 400).subquery()).order_by(desc(Log.timestamp_utc)).limit(10)
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