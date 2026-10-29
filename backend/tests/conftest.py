"""Keep rate-limit state scoped to each test; retain real limits within the test."""

import pytest

from app import limiting


@pytest.fixture(autouse=True)
def isolated_auth_rate_buckets():
    with limiting._lock:
        limiting._buckets.clear()
    yield
    with limiting._lock:
        limiting._buckets.clear()
