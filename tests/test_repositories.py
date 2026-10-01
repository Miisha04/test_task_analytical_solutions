from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

import app.repositories as repos
from app.models import Document
from app.schemas import SearchMode


@pytest.mark.parametrize(
    ("mode", "expected_query"),
    [
        (
            SearchMode.ANY,
            {
                "match": {
                    "text": {
                        "query": "новый скин",
                        "operator": "or",
                    }
                }
            },
        ),
        (
            SearchMode.ALL,
            {
                "match": {
                    "text": {
                        "query": "новый скин",
                        "operator": "and",
                    }
                }
            },
        ),
        (
            SearchMode.PHRASE,
            {
                "match_phrase": {
                    "text": {
                        "query": "новый скин",
                    }
                }
            },
        ),
        (
            SearchMode.FUZZY,
            {
                "match": {
                    "text": {
                        "query": "новый скин",
                        "fuzziness": "AUTO",
                    }
                }
            },
        ),
    ],
)
async def test_search_document_ids_builds_expected_query(
    mode: SearchMode,
    expected_query: dict[str, object],
    monkeypatch,
) -> None:
    search_mock = AsyncMock(
        return_value={
            "hits": {
                "hits": [
                    {"_source": {"id": 4}},
                    {"_source": {"id": 9}},
                ]
            }
        }
    )
    elasticsearch_mock = Mock(search=search_mock)
    monkeypatch.setattr(repos, "elasticsearch", elasticsearch_mock)

    result = await repos.search_document_ids(
        text="новый скин",
        mode=mode,
        limit=10,
    )

    assert result == [4, 9]
    search_mock.assert_awaited_once_with(
        index=repos.DOCUMENTS_INDEX,
        query=expected_query,
        source=["id"],
        size=10,
    )


async def test_delete_document_commits_both_deletions(monkeypatch) -> None:
    document = Document(
        id=7,
        rubrics=["news"],
        text="Document",
        created_date=datetime(2026, 1, 1),
    )
    db = AsyncMock()
    db.get.return_value = document
    delete_from_index = AsyncMock()
    elasticsearch_with_options = Mock(delete=delete_from_index)
    elasticsearch_mock = Mock()
    elasticsearch_mock.options.return_value = elasticsearch_with_options
    monkeypatch.setattr(repos, "elasticsearch", elasticsearch_mock)

    result = await repos.delete_document(document_id=7, db=db)

    assert result is True
    db.get.assert_awaited_once_with(Document, 7)
    db.delete.assert_awaited_once_with(document)
    db.flush.assert_awaited_once_with()
    delete_from_index.assert_awaited_once_with(
        index=repos.DOCUMENTS_INDEX,
        id="7",
        refresh="wait_for",
    )
    db.commit.assert_awaited_once_with()
    db.rollback.assert_not_awaited()
    elasticsearch_mock.options.assert_called_once_with(ignore_status=404)


async def test_delete_document_returns_false_when_not_found(
    monkeypatch,
) -> None:
    db = AsyncMock()
    db.get.return_value = None
    elasticsearch_mock = Mock()
    monkeypatch.setattr(repos, "elasticsearch", elasticsearch_mock)

    result = await repos.delete_document(document_id=9999, db=db)

    assert result is False
    db.delete.assert_not_awaited()
    db.commit.assert_not_awaited()
    elasticsearch_mock.options.assert_not_called()


async def test_delete_document_rolls_back_on_index_error(
    monkeypatch,
) -> None:
    document = Document(
        id=7,
        rubrics=["news"],
        text="Document",
        created_date=datetime(2026, 1, 1),
    )
    db = AsyncMock()
    db.get.return_value = document
    delete_from_index = AsyncMock(side_effect=RuntimeError("index failed"))
    elasticsearch_mock = Mock()
    elasticsearch_mock.options.return_value = Mock(delete=delete_from_index)
    monkeypatch.setattr(repos, "elasticsearch", elasticsearch_mock)

    with pytest.raises(RuntimeError, match="index failed"):
        await repos.delete_document(document_id=7, db=db)

    db.rollback.assert_awaited_once_with()
    db.commit.assert_not_awaited()
