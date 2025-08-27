import httpx
import asyncio
import time
from app.config import MAX_REQUESTS_PER_MINUTE, WINDOW_SECONDS

# Define the target URL for your running proxy
PROXY_URL = "http://localhost:8000/proxy/mock_github/users/google"

TOTAL_REQUESTS =  MAX_REQUESTS_PER_MINUTE + 20
EXPECTED_SUCCESS = MAX_REQUESTS_PER_MINUTE
EXPECTED_BLOCKED = 20

async def make_request(client, i):
    try:
        response = await client.get(PROXY_URL)
        print(f"Request {i+1}: Status {response.status_code}, Remaining: {response.headers.get('X-RateLimit-Remaining')}")
        return response.status_code, response.headers
    except httpx.ReadTimeout:
        print(f"Request {i+1}: Timed out")
        return "Timeout", None


async def main():
    success_count = 0
    blocked_count = 0

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Create a list of tasks to run in parallel
        tasks = [make_request(client, i) for i in range(TOTAL_REQUESTS)]
        
        results = await asyncio.gather(*tasks)

        first_successful_result = next((res for res in results if res[0] == 200), None)

        if first_successful_result:
            _, headers = first_successful_result
            limit_from_header = headers.get('X-RateLimit-Limit')
            print(f"Header 'X-RateLimit-Limit' found: {limit_from_header}")
            assert limit_from_header == str(MAX_REQUESTS_PER_MINUTE)
            print("Test PASSED: Rate limit headers are correct.")
        else:
            print("Test FAILED: Could not find a successful request to verify headers.")


        for status_code, _ in results:
            if status_code == 200:
                success_count += 1
            elif status_code == 429:
                blocked_count += 1
    
    print("\n--- Test Summary ---")
    print(f"Expected successful: {EXPECTED_SUCCESS}, Actual: {success_count}")
    print(f"Expected blocked: {EXPECTED_BLOCKED}, Actual: {blocked_count}")
    print("--------------------")

    if success_count == EXPECTED_SUCCESS and blocked_count == EXPECTED_BLOCKED:
        print("Test PASSED: The rate limiter blocked the correct number of requests.")
    else:
        print("Test FAILED: The number of blocked/successful requests was incorrect.")

    await test_window_reset()

async def test_window_reset():    
    print(f"\nWaiting for {WINDOW_SECONDS} seconds for the window to reset...")
    await asyncio.sleep(WINDOW_SECONDS)

    print("Sending one more request post-reset...")
    async with httpx.AsyncClient() as client:
        response = await client.get(PROXY_URL)
        
    print(f"Final request status: {response.status_code}")
    assert response.status_code == 200
    print("Test PASSED: The rate limit window reset correctly.")

if __name__ == "__main__":
    asyncio.run(main()) 