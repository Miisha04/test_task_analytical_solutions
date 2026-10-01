import argparse
import ast
import asyncio
import csv
from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path

from elasticsearch import helpers
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.elasticsearch import (
    DOCUMENTS_INDEX,
    create_documents_index,
    elasticsearch,
)
from app.models import Document


DEFAULT_CSV_PATH = Path("data/posts.csv")
INDEX_CHUNK_SIZE = 500


class ImportDataError(Exception):
    """Raised when source data cannot be imported safely."""


def parse_rubrics(value: str, row_number: int) -> list[str]:
    try:
        rubrics = ast.literal_eval(value)
    except (SyntaxError, ValueError) as error:
        raise ImportDataError(
            f"Invalid rubrics value in CSV row {row_number}"
        ) from error

    if not isinstance(rubrics, list) or not all(
        isinstance(rubric, str) for rubric in rubrics
    ):
        raise ImportDataError(
            f"Rubrics must be a list of strings in CSV row {row_number}"
        )

    return rubrics


def read_documents(csv_path: Path) -> list[Document]:
    if not csv_path.is_file():
        raise ImportDataError(f"CSV file does not exist: {csv_path}")

    documents: list[Document] = []

    with csv_path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        required_columns = {"text", "created_date", "rubrics"}
        actual_columns = set(reader.fieldnames or [])

        if not required_columns.issubset(actual_columns):
            missing_columns = ", ".join(
                sorted(required_columns - actual_columns)
            )
            raise ImportDataError(
                f"CSV file is missing required columns: {missing_columns}"
            )

        for row_number, row in enumerate(reader, start=2):
            text = row["text"]
            created_date = row["created_date"]
            rubrics = row["rubrics"]

            if not text or not created_date or not rubrics:
                raise ImportDataError(
                    f"CSV row {row_number} contains an empty required value"
                )

            try:
                parsed_date = datetime.fromisoformat(created_date)
            except ValueError as error:
                raise ImportDataError(
                    f"Invalid created_date in CSV row {row_number}"
                ) from error

            documents.append(
                Document(
                    text=text,
                    created_date=parsed_date,
                    rubrics=parse_rubrics(rubrics, row_number),
                )
            )

    if not documents:
        raise ImportDataError("CSV file does not contain any documents")

    return documents


async def import_documents(
    session: AsyncSession,
    csv_path: Path,
) -> int:
    documents_count = await session.scalar(
        select(func.count()).select_from(Document)
    )

    if documents_count:
        raise ImportDataError(
            "The documents table is not empty. "
            "Use --reindex-only to index the existing database rows."
        )

    documents = read_documents(csv_path)
    session.add_all(documents)
    await session.commit()

    return len(documents)


async def document_actions(
    session: AsyncSession,
) -> AsyncIterator[dict[str, object]]:
    statement = (
        select(Document)
        .order_by(Document.id)
        .execution_options(yield_per=INDEX_CHUNK_SIZE)
    )
    documents = await session.stream_scalars(statement)

    async for document in documents:
        yield {
            "_op_type": "index",
            "_index": DOCUMENTS_INDEX,
            "_id": str(document.id),
            "_source": {
                "id": document.id,
                "text": document.text,
            },
        }


async def index_documents(session: AsyncSession) -> int:
    indexed_count, _ = await helpers.async_bulk(
        elasticsearch,
        document_actions(session),
        chunk_size=INDEX_CHUNK_SIZE,
        refresh="wait_for",
    )
    return indexed_count


async def run_import(csv_path: Path, reindex_only: bool) -> None:
    try:
        await create_documents_index()

        async with async_session() as session:
            if not reindex_only:
                imported_count = await import_documents(session, csv_path)
                print(f"Imported {imported_count} documents into PostgreSQL.")

            indexed_count = await index_documents(session)
            print(f"Indexed {indexed_count} documents in Elasticsearch.")
    finally:
        await elasticsearch.close()


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import documents from CSV and index them in Elasticsearch."
    )
    parser.add_argument(
        "csv_path",
        nargs="?",
        type=Path,
        default=DEFAULT_CSV_PATH,
        help=f"CSV path (default: {DEFAULT_CSV_PATH})",
    )
    parser.add_argument(
        "--reindex-only",
        action="store_true",
        help="Skip CSV import and index the existing PostgreSQL rows.",
    )
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()

    try:
        asyncio.run(
            run_import(
                csv_path=arguments.csv_path,
                reindex_only=arguments.reindex_only,
            )
        )
    except ImportDataError as error:
        raise SystemExit(f"Import failed: {error}") from error


if __name__ == "__main__":
    main()
