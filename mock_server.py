from fastapi import FastAPI, Request

app = FastAPI()

@app.api_route("/users/{username}", methods=["GET"])
async def get_user(username: str, request: Request):
    print(f"Mock server received request for user: {username}")
    return {"login": username, "id": 12345, "mock": True}

# To run this server: uvicorn mock_server:app --port 8001