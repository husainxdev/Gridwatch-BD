"""Thread-safe process-local limiter. Multi-worker deployments need ingress limits."""

from collections import deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request

from .config import get_settings

_buckets = {}
_lock = Lock()


def limit_auth(request: Request):
    if request.method != "POST":
        return
    settings = get_settings()
    key = (request.client.host if request.client else "unknown", request.url.path)
    instant = monotonic()
    with _lock:
        expired = [
            k
            for k, values in _buckets.items()
            if not values or values[-1] <= instant - settings.auth_rate_window_seconds
        ]
        for k in expired:
            del _buckets[k]
        values = _buckets.setdefault(key, deque())
        while values and values[0] <= instant - settings.auth_rate_window_seconds:
            values.popleft()
        if len(values) >= settings.auth_rate_limit:
            raise HTTPException(
                429,
                "Too many attempts; try again later",
                headers={"Retry-After": str(settings.auth_rate_window_seconds)},
            )
        values.append(instant)
