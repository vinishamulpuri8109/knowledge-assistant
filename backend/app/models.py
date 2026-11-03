"""ORM models (tables)."""
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ServiceRecord(Base):
    __tablename__ = "service_records"

    service_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    equipment_id: Mapped[str] = mapped_column(String(20), index=True)
    equipment_model: Mapped[str] = mapped_column(String(50))
    issue_description: Mapped[str] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    diagnosis: Mapped[str] = mapped_column(Text)
    resolution: Mapped[str] = mapped_column(Text)
    service_date: Mapped[date] = mapped_column(Date)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    file_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    num_pages: Mapped[int] = mapped_column(Integer, default=0)
    num_chunks: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="processing")  # processing | ready | failed
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class QueryLog(Base):
    __tablename__ = "query_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question: Mapped[str] = mapped_column(Text)
    route: Mapped[str] = mapped_column(String(10))
    tools_used: Mapped[str] = mapped_column(String(200))  # comma-separated
    sufficient_evidence: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
