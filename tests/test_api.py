from datetime import datetime
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

import app.repositories as repos
from app.models import Document
from app.schemas import SearchMode


def test_search_returns_documents(
    client: TestClient,
    fake_db: object,
    monkeypatch,
) -> None:
    document = Document(
        id=1,
        rubrics=["news", "games"],
        text="Новый скин",
        created_date=datetime(2026, 1, 2, 12, 30),
    )
    search_mock = AsyncMock(return_value=[1])
    get_documents_mock = AsyncMock(return_value=[document])
    monkeypatch.setattr(repos, "search_document_ids", search_mock)
    monkeypatch.setattr(repos, "get_documents", get_documents_mock)

    response = client.get(
        "/search-documents",
        params={"input_text": "новый скин"},
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "rubrics": ["news", "games"],
            "text": "Новый скин",
            "created_date": "2026-01-02T12:30:00",
        }
    ]
    search_mock.assert_awaited_once_with(
        text="новый скин",
        mode=SearchMode.ANY,
        limit=20,
    )
    get_documents_mock.assert_awaited_once_with(fake_db, [1])


def test_search_rejects_invalid_limit(client: TestClient) -> None:
    response = client.get(
        "/search-documents",
        params={"input_text": "python", "limit": 21},
    )

    assert response.status_code == 422


def test_search_rejects_unknown_mode(client: TestClient) -> None:
    response = client.get(
        "/search-documents",
        params={"input_text": "python", "mode": "unknown"},
    )

    assert response.status_code == 422


def test_search_returns_503_when_storage_fails(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        repos,
        "search_document_ids",
        AsyncMock(side_effect=SQLAlchemyError("storage unavailable")),
    )

    response = client.get(
        "/search-documents",
        params={"input_text": "python"},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Search service is unavailable"}


def test_delete_returns_204(
    client: TestClient,
    fake_db: object,
    monkeypatch,
) -> None:
    delete_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(repos, "delete_document", delete_mock)

    response = client.delete(
        "/delete-document",
        params={"document_id": 7},
    )

    assert response.status_code == 204
    assert response.content == b""
    delete_mock.assert_awaited_once_with(document_id=7, db=fake_db)


def test_delete_returns_404(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        repos,
        "delete_document",
        AsyncMock(return_value=False),
    )

    response = client.delete(
        "/delete-document",
        params={"document_id": 9999},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Document not found"}


def test_delete_returns_503_when_storage_fails(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        repos,
        "delete_document",
        AsyncMock(side_effect=SQLAlchemyError("storage unavailable")),
    )

    response = client.delete(
        "/delete-document",
        params={"document_id": 7},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Storage service is unavailable"}
