import redis.asyncio as redis
import json
from .config import REDIS_URL, CACHE_EXPIRY_SECONDS

redis_client = redis.from_url(REDIS_URL, decode_responses=True)

async def get_cached_response(cache_key: str):
    result = await redis_client.get(cache_key)

    if result is not None:
        return json.loads(result)
    return None

async def set_cached_response(cache_key: str, response_data: dict):
    json_response = json.dumps(response_data)
    
    await redis_client.setex(cache_key, CACHE_EXPIRY_SECONDS, json_response)

