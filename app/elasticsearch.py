import os

from elasticsearch import AsyncElasticsearch


DOCUMENTS_INDEX = "documents"

DOCUMENTS_MAPPING = {
    "dynamic": "strict",
    "properties": {
        "id": {
            "type": "long",
        },
        "text": {
            "type": "text",
            "analyzer": "russian",
        },
    },
}


elasticsearch = AsyncElasticsearch(
    os.getenv(
        "ELASTICSEARCH_URL",
        "http://localhost:9200",
    )
)


async def create_documents_index() -> None:
    exists = await elasticsearch.indices.exists(
        index=DOCUMENTS_INDEX,
    )

    if not exists:
        await elasticsearch.indices.create(
            index=DOCUMENTS_INDEX,
            mappings=DOCUMENTS_MAPPING,
        )