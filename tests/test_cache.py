import httpx
import asyncio
import json
import redis.asyncio as redis
from app.config import CACHE_EXPIRY_SECONDS

BASE_URL = "http://localhost:8000/proxy/mock_github"
REDIS_URL = "redis://localhost:6379"

redis_client = redis.from_url(REDIS_URL, decode_responses=True)


def create_cache_key(path: str, params: dict = None) -> str:
    """Helper function to create the cache key exactly as in main.py"""
    params = params or {}
    params_dict = dict(params)
    serialized_params = json.dumps(params_dict, sort_keys=True)
    return f"cache:mock_github:{path}:{serialized_params}"


async def test_cache_miss_and_population():
    print("\n--- Running Test: Cache Miss and Population ---")
    await redis_client.flushdb()
    
    test_path = "/users/test_miss"
    url = f"{BASE_URL}{test_path}"
    cache_key = create_cache_key("users/test_miss")

    async with httpx.AsyncClient() as client:
        response = await client.get(url)

    assert response.status_code == 200
    exists = await redis_client.exists(cache_key)
    assert exists == 1
    
    print("Test PASSED: First request was successful and populated the cache.")


async def test_cache_hit():
    print("\n--- Running Test: Cache Hit ---")
    await redis_client.flushdb()

    test_path = "/users/test_hit"
    url = f"{BASE_URL}{test_path}"
    cache_key = create_cache_key("users/test_hit")

    async with httpx.AsyncClient() as client:
        await client.get(url)

    poisoned_data = {
        "content": {"message": "this is from the cache"},
        "status_code": 201,
        "headers": {"X-Cache-Status": "Hit"}
    }
    await redis_client.set(cache_key, json.dumps(poisoned_data))

    async with httpx.AsyncClient() as client:
        response = await client.get(url)

    assert response.status_code == 201
    assert response.json() == {"message": "this is from the cache"}
    assert response.headers["x-cache-status"] == "Hit"
    
    print("Test PASSED: Second request was correctly served from the cache.")


async def test_cache_bypassed_for_different_params():
    print("\n--- Running Test: Cache Bypassed for Different Params ---")
    await redis_client.flushdb()

    test_path = "/users/test_params"
    cache_key_a = create_cache_key("users/test_params", {"param": "A"})
    cache_key_b = create_cache_key("users/test_params", {"param": "B"})

    async with httpx.AsyncClient() as client:
        await client.get(f"{BASE_URL}{test_path}?param=A")
        await client.get(f"{BASE_URL}{test_path}?param=B")

    assert await redis_client.exists(cache_key_a) == 1
    assert await redis_client.exists(cache_key_b) == 1
    
    print("Test PASSED: Requests with different params were cached separately.")


async def test_cache_bypassed_for_post_request():
    print("\n--- Running Test: Cache Bypassed for POST Request ---")
    await redis_client.flushdb()
    
    test_path = "/users/test_post"
    url = f"{BASE_URL}{test_path}"
    cache_key = create_cache_key("users/test_post")

    async with httpx.AsyncClient() as client:
        await client.post(url, json={"data": "value"})
    
    exists = await redis_client.exists(cache_key)
    assert exists == 0
    
    print("Test PASSED: POST request did not populate the cache.")


async def test_cache_expiration():
    print("\n--- Running Test: Cache Expiration ---")
    if CACHE_EXPIRY_SECONDS != 1:
        print("Test SKIPPED: CACHE_EXPIRY_SECONDS in config.py must be set to 1 for this test.")
        return

    await redis_client.flushdb()
    test_path = "/users/test_expiry"
    url = f"{BASE_URL}{test_path}"
    cache_key = create_cache_key("users/test_expiry")

    async with httpx.AsyncClient() as client:
        await client.get(url)

    await asyncio.sleep(1.1)
    
    exists = await redis_client.exists(cache_key)
    assert exists == 0
    
    print("Test PASSED: Cache entry expired successfully.")


async def main():
    print("=====================")
    print("  Running Cache Tests  ")
    print("=====================")
    
    try:
        await test_cache_miss_and_population()
        await test_cache_hit()
        await test_cache_bypassed_for_different_params()
        await test_cache_bypassed_for_post_request()
        await test_cache_expiration()
        print("\n=========================")
        print("  All tests completed.   ")
        print("=========================")
    except httpx.ConnectError:
        print("\n[ERROR] Connection failed. Is the proxy server running on localhost:8000?")
    except AssertionError as e:
        print(f"\n[ASSERTION FAILED] {e}")
        print("One or more tests failed.")
    finally:
        await redis_client.aclose()


if __name__ == "__main__":
    asyncio.run(main())