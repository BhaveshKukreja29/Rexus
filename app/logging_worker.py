import asyncio
import json
import logging
from datetime import datetime
from .database import AsyncSessionLocal
from .models import Log
from .cache import redis_client

def json_decode_hook(dct):
    if 'timestamp_utc' in dct:
        dct['timestamp_utc'] = datetime.fromisoformat(dct['timestamp_utc'])
    return dct

async def batch_log_writer():
    while True:
        await asyncio.sleep(60)
        try:
            pipe = redis_client.pipeline()
            pipe.lrange("api_log_buffer", 0, -1)
            pipe.delete("api_log_buffer")
            logs_to_write_json, _ = await pipe.execute()

            if not logs_to_write_json:
                continue

            logs_to_write = [json.loads(log, object_hook=json_decode_hook) for log in logs_to_write_json]
            
            async with AsyncSessionLocal() as session:
                session.add_all([Log(**log_data) for log_data in logs_to_write])
                await session.commit()
                logging.info(f"Successfully wrote {len(logs_to_write)} logs to the database.")
        
        except Exception as e:
            logging.error(f"!!! CRITICAL ERROR in log writer: {e}", exc_info=True)