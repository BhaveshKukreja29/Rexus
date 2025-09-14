from fastapi import FastAPI, Request, HTTPException, status, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from httpx import AsyncClient, ConnectError, ReadTimeout
from .config import API_TARGETS, MAX_REQUESTS_PER_MINUTE, WINDOW_SECONDS, MAX_REQUEST_SIZE
from .rate_limit import rate_limit
from .cache import get_cached_response, set_cached_response, redis_client
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s') 
import json
from .auth import router
from .security import authenticate_api_key
from .models import APIKey
from datetime import datetime, timezone
from contextlib import asynccontextmanager
import asyncio
from .logging_worker import batch_log_writer
from .analytics import router as analytics_router
from fastapi import WebSocket, WebSocketDisconnect
from typing import List

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    log_task = asyncio.create_task(batch_log_writer())
    yield
    log_task.cancel()
    try:
        await log_task
    except asyncio.CancelledError:
        logging.info("Log writer task cancelled.")


app = FastAPI(lifespan=lifespan)

app.include_router(router)
app.include_router(analytics_router)

origins = [
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_target_url(api_name: str) -> str:
    target_url = API_TARGETS.get(api_name)
    if not target_url:
        raise HTTPException(status_code=400, detail="Invalid API name provided.")
    return target_url


@app.api_route('/proxy/{api_name}/{path:path}', methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_request(
    api_name: str, 
    path: str, 
    request: Request,
    api_key: APIKey = Depends(authenticate_api_key)
):
    try:
        current_requests, timestamp = await rate_limit(
            key_id=api_key.public_id, 
            limit=api_key.requests_per_minute_limit
        )
        
        fresh_rate_limit_headers = {
            "X-RateLimit-Limit": str(api_key.requests_per_minute_limit),
            "X-RateLimit-Remaining": str(api_key.requests_per_minute_limit - current_requests),
            "X-RateLimit-Reset": str(timestamp + WINDOW_SECONDS)
        }
        
        # check for cached values
        if request.method == "GET":
            query_parameters = dict(request.query_params)
            serialized_query_parametes = json.dumps(query_parameters, sort_keys=True)
            cache_key = f"cache:{api_name}:{path}:{serialized_query_parametes}"

            cached_response = await get_cached_response(cache_key)
            if cached_response is not None:
                log_entry = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "http_method": request.method, "request_path": path, "status_code": cached_response["status_code"], "user_id": api_key.user_id}
                log_entry_json = json.dumps(log_entry)
                await redis_client.lpush("api_log_buffer", log_entry_json)
                await manager.broadcast(log_entry_json)

                response_headers = cached_response["headers"]
                response_headers.update(fresh_rate_limit_headers)
                response_headers.pop("content-length", None)
                return Response(
                    content=json.dumps(cached_response["content"]),
                    status_code=cached_response["status_code"], 
                    headers=response_headers
                )
        
        # If not cached, proceed to proxy the request
        body = await request.body()
        request_size = len(body)

        if request_size > MAX_REQUEST_SIZE:
            raise HTTPException(status_code=413, detail="Payload Too Large")

        async with AsyncClient() as client:
            # remove the client's 'host' header, as it's specific to the incoming connection
            # we don't want the actual api to recieve "localhost:8000", it will think something's wrong
            # also, header keys are lowercased by the ASGI server, so we just use 'host'
            request_headers = dict(request.headers)
            request_headers.pop("host", None)

            base_url = get_target_url(api_name)  
            target_url = f"{base_url}/{path}"

            try:
                response = await client.request(
                    method=request.method, 
                    url=target_url, 
                    headers=request_headers, 
                    params=request.query_params,
                    content=body
                )
            except (ConnectError, ReadTimeout):
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="The upstream API is unavailable."
                )
            
            log_entry = {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "http_method": request.method,
                "request_path": path,
                "status_code": response.status_code,
                "user_id": api_key.user_id,
            }
            log_entry_json = json.dumps(log_entry)
            await redis_client.lpush("api_log_buffer", log_entry_json)
            await manager.broadcast(log_entry_json)


            # remove hop-by-hop headers from the target's response
            # this allows our server to generate correct headers for the client
            response_headers = dict(response.headers)
            response_headers.pop("content-encoding", None)
            response_headers.pop("content-length", None)
            response_headers.pop("transfer-encoding", None)
            response_headers.pop("connection", None)


            # I learned that X means experimental header, which are different from the standard ones
            # Although it was depreceated in 2012, it's still widely used
            response_headers.pop("x-ratelimit-limit", None)
            response_headers.pop("x-ratelimit-remaining", None)
            response_headers.pop("x-ratelimit-reset", None)
            
            # Add our fresh rate limit headers
            response_headers.update(fresh_rate_limit_headers)

            logging.info(f"Proxying request: {request.method} {target_url} - Status: {response.status_code}")

            if request.method == "GET" and response.status_code == 200:
                # Cache the original response from the upstream API, not our modified one
                response_dict = {
                    "content": response.json(), 
                    "status_code": response.status_code, 
                    "headers": dict(response.headers) 
                }
                await set_cached_response(cache_key, response_dict)

            return Response(
                content=response.content, 
                status_code=response.status_code, 
                headers=response_headers
            )

    except HTTPException as e:
        if e.status_code == 429:
            log_entry = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "http_method": request.method, "request_path": path, "status_code": 429, "user_id": api_key.user_id}
            log_entry_json = json.dumps(log_entry)
            await redis_client.lpush("api_log_buffer", log_entry_json)
            await manager.broadcast(log_entry_json)
        
        # re-raise the exception so FastAPI can send response to client
        raise e
    
@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)