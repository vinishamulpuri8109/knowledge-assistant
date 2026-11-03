"""Pydantic request/response schemas for the REST API."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Route = Literal["docs", "db", "both", "none"]


class ServiceRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    service_id: str
    equipment_id: str
    equipment_model: str
    issue_description: str
    error_code: str | None
    diagnosis: str
    resolution: str
    service_date: date


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    num_pages: int
    num_chunks: int
    status: str
    error: str | None
    uploaded_at: datetime


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)


class Citation(BaseModel):
    document_id: str
    document_name: str
    page: int
    excerpt: str
    distance: float


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    service_records: list[ServiceRecordOut]
    tools_used: list[str]
    route: Route
    sufficient_evidence: bool
    errors: list[str] = []


class RecentQuery(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    question: str
    route: str
    tools_used: str
    sufficient_evidence: bool
    created_at: datetime


class DashboardStats(BaseModel):
    total_documents: int
    ready_documents: int
    total_chunks: int
    equipment_count: int
    service_record_count: int
    recent_queries: list[RecentQuery]
    recent_incidents: list[ServiceRecordOut]
    llm_configured: bool
