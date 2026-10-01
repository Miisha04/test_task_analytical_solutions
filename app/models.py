from datetime import datetime

from sqlalchemy import Integer, String, DateTime, ARRAY, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    rubrics: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
    )

    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_date: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )