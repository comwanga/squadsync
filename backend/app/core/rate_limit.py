import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import HTTPException, Request


_hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)
_lock = threading.Lock()


def rate_limit(name: str, requests: int, window_seconds: int = 60) -> Callable:
    """Return a lightweight per-process, per-client fixed-route rate limiter."""

    def check(request: Request) -> None:
        client = request.client.host if request.client else "unknown"
        key = (name, client)
        now = time.monotonic()
        cutoff = now - window_seconds
        with _lock:
            timestamps = _hits[key]
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()
            if len(timestamps) >= requests:
                raise HTTPException(status_code=429, detail="Too many requests. Try again later.")
            timestamps.append(now)

    return check


def clear_rate_limits() -> None:
    """Clear process-local counters; used to isolate the test suite."""
    with _lock:
        _hits.clear()
