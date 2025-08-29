import redis.asyncio as redis
import time
import uuid
from fastapi import HTTPException
from .config import REDIS_URL, MAX_REQUESTS_PER_MINUTE, WINDOW_SECONDS

redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# This rate limiter uses the Sliding Window algorithm implemented with a Redis Sorted Set.
#
# Initial designs considered a simple Redis List, but that was
# rejected as it was not scalable. The naive approach required fetching all request
# timestamps to the client for filtering, which creates a performance bottleneck under load.
#
# This implementation offloads all heavy lifting to Redis. It uses a pipeline to atomically
# execute four commands in a single network trip: clean old records (ZREMRANGEBYSCORE),
# add the new request (ZADD), count the current requests (ZCARD), and set an expiry for
# garbage collection. 

async def rate_limit(key_id: str, limit: int):
    now = int(time.time())

    redis_key = f"rate_limit:{key_id}"

    time_window = now - WINDOW_SECONDS

    pipe = redis_client.pipeline()

    pipe.zremrangebyscore(redis_key, 0, time_window)

    unique_request_id = f"{now}{uuid.uuid4()}"
    pipe.zadd(redis_key, {unique_request_id: now})

    pipe.zcard(redis_key)

    pipe.expire(redis_key, WINDOW_SECONDS)

    results = await pipe.execute()

    # index 2 cuz the third command is what actually counts the requests in window
    current_requests = results[2]

    if current_requests > limit:
        raise HTTPException(status_code=429, detail="Too many requests")
    
    return current_requests, now

