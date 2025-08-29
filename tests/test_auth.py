import httpx
import asyncio

BASE_URL = "http://localhost:8000"
AUTH_URL = f"{BASE_URL}/auth/keys"
PROXY_URL = f"{BASE_URL}/proxy/mock_github/users/testuser"

valid_api_key = None

async def test_create_api_key_success():
    global valid_api_key
    print("\n--- Running Test: Create API Key Success ---")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(AUTH_URL, json={"user_id": "test-auth-user"})

    assert response.status_code == 201, f"Expected 201, got {response.status_code}"
    response_json = response.json()
    assert "api_key" in response_json, "Response JSON missing 'api_key'"
    
    api_key = response_json["api_key"]
    assert api_key.startswith("akp_"), "API key prefix is incorrect"
    assert "." in api_key, "API key format is missing the separator"
    
    valid_api_key = api_key  
    print("Test PASSED: API key created successfully.")

async def test_proxy_access_no_key():
    print("\n--- Running Test: Proxy Access with No Key ---")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(PROXY_URL)
    
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    print("Test PASSED: Request was correctly unauthorized.")

async def test_proxy_access_bad_key_format():
    print("\n--- Running Test: Proxy Access with Bad Key Format ---")
    
    headers = {"Authorization": "Bearer badlyformattedkey"}
    async with httpx.AsyncClient() as client:
        response = await client.get(PROXY_URL, headers=headers)
        
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    print("Test PASSED: Request was correctly unauthorized.")

async def test_proxy_access_invalid_key():
    print("\n--- Running Test: Proxy Access with Invalid Key ---")
    
    fake_key = "akp_12345abcde.fghij67890"
    headers = {"Authorization": f"Bearer {fake_key}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(PROXY_URL, headers=headers)
        
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    print("Test PASSED: Request was correctly unauthorized.")

async def test_proxy_access_valid_key():
    print("\n--- Running Test: Proxy Access with Valid Key ---")
    
    assert valid_api_key is not None, "Cannot run test, valid API key was not created."
    
    headers = {"Authorization": f"Bearer {valid_api_key}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(PROXY_URL, headers=headers)
        
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print("Test PASSED: Request was successfully authorized.")
    
async def main():
    print("========================")
    print("  Running Auth Tests  ")
    print("========================")
    
    try:
        await test_create_api_key_success()
        await test_proxy_access_no_key()
        await test_proxy_access_bad_key_format()
        await test_proxy_access_invalid_key()
        await test_proxy_access_valid_key()
        print("\n=========================")
        print("  All tests completed.  ")
        print("=========================")
    except httpx.ConnectError:
        print("\n[ERROR] Connection failed. Is the proxy server running?")
    except AssertionError as e:
        print(f"\n[ASSERTION FAILED] {e}")
        print("One or more tests failed.")

if __name__ == "__main__":
    asyncio.run(main())