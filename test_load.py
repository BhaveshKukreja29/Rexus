import httpx
import asyncio
import time

# Define the target URL for your running proxy
PROXY_URL = "http://localhost:8000/proxy/github/users/google"

TOTAL_REQUESTS = 120 
CONCURRENT_REQUESTS = 15 

async def make_request(client, i):
    try:
        response = await client.get(PROXY_URL)
        print(f"Request {i+1}: Status {response.status_code}")
        return response.status_code
    except httpx.ReadTimeout:
        print(f"Request {i+1}: Timed out")
        return "Timeout"


async def main():
    success_count = 0
    blocked_count = 0

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Create a list of tasks to run in parallel
        tasks = [make_request(client, i) for i in range(TOTAL_REQUESTS)]
        
        results = await asyncio.gather(*tasks)

        for status_code in results:
            if status_code == 200:
                success_count += 1
            elif status_code == 429:
                blocked_count += 1
    
    print("\n--- Test Summary ---")
    print(f"Successful requests (200 OK): {success_count}")
    print(f"Blocked requests (429 Too Many Requests): {blocked_count}")
    print("--------------------")

    if blocked_count > 0:
        print("Test PASSED: The rate limiter is working correctly.")
    else:
        print("Test FAILED: The rate limiter did not block any requests.")


if __name__ == "__main__":
    asyncio.run(main())