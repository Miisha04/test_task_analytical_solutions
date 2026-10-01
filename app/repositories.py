from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document
from app.schemas import SearchMode

from app.elasticsearch import (
    elasticsearch,
    DOCUMENTS_INDEX
)

async def search_document_ids(
    text: str,
    mode: SearchMode = SearchMode.ANY,
    limit: int = 20,
) -> list[int]:
    
    if mode == SearchMode.PHRASE:
        elastic_query = {
            "match_phrase": {
                "text": {
                    "query": text,
                }
            }
        }

    elif mode == SearchMode.FUZZY:
        elastic_query = {
            "match": {
                "text": {
                    "query": text,
                    "fuzziness": "AUTO",
                }
            }
        }

    else:
        elastic_query = {
            "match": {
                "text": {
                    "query": text,
                    "operator": (
                        "and"
                        if mode == SearchMode.ALL
                        else "or"
                    ),
                }
            }
        }

    response = await elasticsearch.search(
        index=DOCUMENTS_INDEX,
        query=elastic_query,
        source=["id"],
        size=limit,
    )

    return [
        hit["_source"]["id"]
        for hit in response["hits"]["hits"]
    ]


async def get_documents(
    db: AsyncSession,
    docs_ids: list[int]
) -> list[Document]:

    if not docs_ids:
        return []

    result = (await db.execute(
        select(Document)
        .where(Document.id.in_(docs_ids))
        .order_by(Document.created_date.desc())
    )).scalars().all()

    return list(result)


async def delete_document(
    document_id: int,
    db: AsyncSession,
) -> bool:
    document = await db.get(Document, document_id)

    if document is None:
        return False

    try:
        await db.delete(document)
        await db.flush()

        await elasticsearch.options(
            ignore_status=404,
        ).delete(
            index=DOCUMENTS_INDEX,
            id=str(document_id),
            refresh="wait_for",
        )

        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return True
