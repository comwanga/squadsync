import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.core.rate_limit import rate_limit


def test_rate_limit_rejects_requests_over_the_window_limit():
    request = Request({"type": "http", "client": ("203.0.113.10", 1234)})
    check = rate_limit("test-route", requests=2)

    check(request)
    check(request)
    with pytest.raises(HTTPException) as exc:
        check(request)
    assert exc.value.status_code == 429
