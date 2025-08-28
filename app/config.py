API_TARGETS = {
    "github": "https://api.github.com",
    "mock_github": "http://mock_server:8001"
}

REDIS_URL = "redis://redis:6379"

MAX_REQUEST_SIZE = 10 * 1024 * 1024

MAX_REQUESTS_PER_MINUTE = 100
WINDOW_SECONDS = 60

CACHE_EXPIRY_SECONDS = 300