import asyncio
import logging
from celery import Celery
from uuid import UUID

from app.config import REDIS_URL
from app.database import AsyncSessionLocal
from app.models import Logs

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

celery_app = Celery("tasks", broker=REDIS_URL, backend=REDIS_URL)


# async helper function to handle the database session and writing.
async def _write_log_to_db(api_key_id: str, method: str, path: str, status_code: int, latency_ms: int):
    async with AsyncSessionLocal() as session:
        # note: We don't pass 'created_at'; the database sets this automatically.
        new_log = Logs(
            api_key_id=UUID(api_key_id), # Convert the string ID back to a UUID object
            method=method,
            path=path,
            status_code=status_code,
            latency_ms=latency_ms
        )
        session.add(new_log)
        await session.commit()

# This is a regular sync function, but .delay() in main.py calls it
# asynchronously by putting it on the Redis queue.
@celery_app.task
def log_request_task(api_key_id, method, path, status_code, latency_ms):
    logging.info(f"Logging request for API Key ID: {api_key_id}")
    asyncio.run(_write_log_to_db(api_key_id, method, path, status_code, latency_ms))
    logging.info(f"Log for API Key ID: {api_key_id} successfully written to DB.")

