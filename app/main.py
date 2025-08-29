from fastapi import FastAPI, Request, HTTPException, status, Response, Depends
from httpx import AsyncClient, ConnectError, ReadTimeout
from .config import API_TARGETS, MAX_REQUESTS_PER_MINUTE, WINDOW_SECONDS, MAX_REQUEST_SIZE
from .rate_limit import rate_limit
from .cache import get_cached_response, set_cached_response
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s') 
import json
import auth
from .security import authenticate_api_key
from .models import APIKey

app = FastAPI()

app.include_router(auth.router)

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
    current_requests, timestamp = await rate_limit(
        key_id=api_key.public_id, 
        limit=api_key.requests_per_minute_limit
    )

    
    body = await request.body()
    request_size = len(body)

    if request_size > MAX_REQUEST_SIZE:
        raise HTTPException(status_code=413, detail="Payload Too Large")
    
    # check for cached values
    if request.method == "GET":
        query_parameters = dict(request.query_params)
        serialized_query_parametes = json.dumps(query_parameters, sort_keys=True)
        cache_key = f"cache:{api_name}:{path}:{serialized_query_parametes}"

        cached_response = await get_cached_response(cache_key)
        if cached_response is not None:
            return Response(
                content=json.dumps(cached_response["content"]),
                status_code=cached_response["status_code"], 
                headers=cached_response["headers"]
            )


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

        response_headers["X-RateLimit-Limit"] = str(api_key.requests_per_minute_limit)
        response_headers["X-RateLimit-Remaining"] = str(api_key.requests_per_minute_limit - current_requests)
        response_headers["X-RateLimit-Reset"] = str(timestamp + WINDOW_SECONDS)

        logging.info(f"Proxying request: {request.method} {target_url} - Status: {response.status_code}")

        if request.method == "GET" and response.status_code == 200:
            response_dict = {
                "content": response.json(), 
                "status_code": response.status_code, 
                "headers": dict(response_headers)
            }
            await set_cached_response(cache_key, response_dict)

        return Response(
            content=response.content, 
            status_code=response.status_code, 
            headers=response_headers
        )
    
