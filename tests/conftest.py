from collections.abc import AsyncIterator, Iterator

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app


@pytest.fixture
def fake_db() -> object:
    return object()


@pytest.fixture
def client(fake_db: object) -> Iterator[TestClient]:
    async def override_get_db() -> AsyncIterator[object]:
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)

    yield test_client

    app.dependency_overrides.clear()
    test_client.close()
