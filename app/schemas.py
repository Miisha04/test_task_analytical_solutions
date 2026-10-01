from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: int
    rubrics: list[str]
    text: str
    created_date: datetime


class SearchMode(StrEnum):
    ANY = "any"
    ALL = "all"
    PHRASE = "phrase"
    FUZZY = "fuzzy"


