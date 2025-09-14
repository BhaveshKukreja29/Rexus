import httpx
import asyncio
import random
import time

BASE_URL = "http://localhost:8000"
AUTH_URL = f"{BASE_URL}/auth/keys"
PROXY_URL = f"{BASE_URL}/proxy"

USER_ID = "log-generator-user"
NUM_REQUESTS = 150

# A pool of realistic paths and methods to generate varied logs
REQUEST_POOL = [
    ("mock_github", "/users/google", "GET"),
    ("mock_github", "/users/apple", "GET"),
    ("mock_github", "/orgs/github", "GET"),
    ("mock_github", "/repos/facebook/react", "GET"),
    ("mock_github", "/users/bhaveshkukreja29", "POST"), # Non-GET to bypass cache
    ("mock_github", "/users/someuser/settings", "PUT"), # Non-GET to bypass cache
    ("non_existent_api", "/some/path", "GET"), # This will cause a 400 error
    ("mock_github", "/not/a/real/path", "GET"), # This will cause a 404 from the mock server
]

async def generate_log(client: httpx.AsyncClient, i: int):
    api_name, path, method = random.choice(REQUEST_POOL)
    url = f"{PROXY_URL}/{api_name}{path}"
    
    try:
        if method == "GET":
            response = await client.get(url)
        elif method == "POST":
            response = await client.post(url, json={"data": "sample"})
        else: # PUT
            response = await client.put(url, json={"data": "update"})
            
        print(f"Request {i+1}/{NUM_REQUESTS}: {method} {url} -> Status {response.status_code}")
    except httpx.RequestError as e:
        print(f"Request {i+1}/{NUM_REQUESTS}: FAILED - {e}")

async def main():
    print("--- Starting Log Generation ---")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(AUTH_URL, json={"user_id": USER_ID})
            response.raise_for_status()
            api_key = response.json()["api_key"]
            print(f"Successfully created API key for user '{USER_ID}'.")
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            print(f"FATAL: Could not create API key. Is the server running? Error: {e}")
            return

    headers = {"Authorization": f"Bearer {api_key}"}
    async with httpx.AsyncClient(headers=headers, timeout=20.0) as client:
        print("--- Sending requests sequentially to generate logs ---")
        for i in range(NUM_REQUESTS):
            await asyncio.sleep(0.2) 
            await generate_log(client, i)

    print("\n--- Log Generation Complete ---")
    print(f"{NUM_REQUESTS} log entries have been sent to the buffer.")

if __name__ == "__main__":
    asyncio.run(main())