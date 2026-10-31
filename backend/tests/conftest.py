from collections.abc import Iterator

import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def clear_cache() -> Iterator[None]:
    """Throttle counters and cached place searches must not leak between tests."""
    cache.clear()
    yield
    cache.clear()
