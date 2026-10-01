
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from elasticsearch import ApiError
from sqlalchemy.exc import SQLAlchemyError

from app.database import get_db
from app.schemas import DocumentResponse, SearchMode

import app.repositories as repos


router = APIRouter()


@router.get(
    "/search-documents",
    response_model=list[DocumentResponse],
    status_code=status.HTTP_200_OK
)
async def search_documents(
    limit: int = Query(20, ge=1, le=20),
    input_text: str = Query(..., min_length=1),
    mode: SearchMode = Query(SearchMode.ANY),
    db: AsyncSession = Depends(get_db)
) -> list[DocumentResponse]:

    try:
        docs_ids = await repos.search_document_ids(
            text=input_text, 
            mode=mode,
            limit=limit
        )
        docs_obj = await repos.get_documents(db, docs_ids)

        docs = [
            DocumentResponse.model_validate(d) 
            for d in docs_obj
        ]

        return docs
    except (ApiError, SQLAlchemyError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Search service is unavailable",
        ) from error


@router.delete(
    "/delete-document",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
) -> None:
    try:
        deleted = await repos.delete_document(
            document_id=document_id,
            db=db,
        )
    except (ApiError, SQLAlchemyError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage service is unavailable",
        ) from error

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )