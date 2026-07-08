"""Rate limiter (slowapi), keyed by client IP.

Behind the reverse proxy the real client IP comes from X-Forwarded-For; uvicorn
must be run with --forwarded-allow-ips so request.client reflects it (see the
Dockerfile). The default in-memory storage is per-process — fine for a single
uvicorn worker; for multiple workers/instances use a shared store (Redis) via
slowapi's storage_uri.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import DEFAULT_RATE_LIMIT, RATE_LIMIT_ENABLED

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[DEFAULT_RATE_LIMIT],
    enabled=RATE_LIMIT_ENABLED,
)
