import pytest

from depends.depends import make_fake_request


@pytest.fixture
def fake_request():
    """Fresh fake request per test."""
    return make_fake_request()


@pytest.fixture
def event_loop():
    """
    Needed for asyncio tests on some pytest configs.
    """
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
