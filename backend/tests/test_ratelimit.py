"""Integration tests for rate limiting and the metrics endpoint.

Uses TestClient WITHOUT a context manager so the lifespan (and thus the heavy
model load) does not run — the model stays unloaded, allowed /api/tts requests
return 503, and requests over the limit return 429. This keeps the test fast
while still exercising the rate-limit wiring.
"""

from fastapi.testclient import TestClient

from app.config import TTS_RATE_LIMIT
from app.main import app

client = TestClient(app)


def _limit() -> int:
    # "10/minute" -> 10
    return int(TTS_RATE_LIMIT.split("/")[0])


def test_metrics_endpoint_exposed():
    resp = client.get("/metrics")
    assert resp.status_code == 200
    # Prometheus exposition format contains standard metric families.
    assert "python_info" in resp.text or "http_request" in resp.text


def test_tts_rate_limited_after_limit():
    limit = _limit()
    statuses = [
        client.post("/api/tts", json={"text": "тест"}).status_code
        for _ in range(limit + 2)
    ]
    # At least one request beyond the limit is rejected with 429.
    assert 429 in statuses
    # Allowed requests are not rate-limited (503 here because the model is not
    # loaded in the test environment); no unexpected status codes.
    assert all(s in (200, 503, 429) for s in statuses)
    # No more than `limit` requests were allowed through before the 429.
    assert statuses.count(429) >= 2
