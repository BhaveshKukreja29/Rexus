from fastapi import FastAPI, Request, HTTPException, status, Response
from httpx import AsyncClient
from .config import API_TARGETS
from .rate_limit import rate_limit

app = FastAPI()

MAX_REQUEST_SIZE = 10 * 1024 * 1024

def get_target_url(api_name: str) -> str:
    target_url = API_TARGETS.get(api_name)
    if not target_url:
        raise HTTPException(status_code=400, detail="Invalid API name provided.")
    return target_url


@app.api_route('/proxy/{api_name}/{path:path}', methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_request(api_name: str, path: str, request: Request):
    await rate_limit(user_id="test-user")
    
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

        response = await client.request(
            method=request.method, 
            url=target_url, 
            headers=request_headers, 
            content=body
        )

        # remove hop-by-hop headers from the target's response
        # this allows our server to generate correct headers for the client
        response_headers = dict(response.headers)
        response_headers.pop("content-encoding", None)
        response_headers.pop("content-length", None)
        response_headers.pop("transfer-encoding", None)
        response_headers.pop("connection", None)

        print(f"Proxying request: {request.method} {target_url} - Status: {response.status_code}")

        return Response(
            content=response.content, 
            status_code=response.status_code, 
            headers=response_headers
        )

