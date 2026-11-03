"""Agent tools. The LLM may only choose a tool and supply validated arguments;
it never writes SQL. All queries are fixed SQLAlchemy statements with bound parameters."""
import re

from langchain_core.tools import tool
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import desc, or_, select

from app.database import get_sessionmaker
from app.models import ServiceRecord
from app.rag import retrieve
from app.schemas import Citation, ServiceRecordOut

EQUIPMENT_ID_RE = re.compile(r"^[A-Z]{1,4}-\d{1,6}$")
KEYWORD_RE = re.compile(r"^[A-Za-z0-9 \-]{2,50}$")


class EquipmentIdInput(BaseModel):
    equipment_id: str = Field(description="Equipment/machine ID, e.g. 'M-102'")

    @field_validator("equipment_id")
    @classmethod
    def check_id(cls, v: str) -> str:
        v = v.strip().upper()
        if not EQUIPMENT_ID_RE.match(v):
            raise ValueError("equipment_id must look like 'M-102'")
        return v


class KeywordInput(BaseModel):
    issue_keyword: str = Field(description="Issue keyword or error code, e.g. 'overheating' or 'E104'")

    @field_validator("issue_keyword")
    @classmethod
    def check_keyword(cls, v: str) -> str:
        v = v.strip()
        if not KEYWORD_RE.match(v):
            raise ValueError("issue_keyword must be 2-50 letters, digits, spaces or hyphens")
        return v


class ManualQueryInput(BaseModel):
    query: str = Field(min_length=2, max_length=500, description="Natural-language search query for the manuals")


def _to_out(rows) -> list[ServiceRecordOut]:
    return [ServiceRecordOut.model_validate(r) for r in rows]


def fetch_service_history(equipment_id: str) -> list[ServiceRecordOut]:
    equipment_id = EquipmentIdInput(equipment_id=equipment_id).equipment_id
    stmt = (select(ServiceRecord)
            .where(ServiceRecord.equipment_id == equipment_id)
            .order_by(desc(ServiceRecord.service_date)))
    with get_sessionmaker()() as db:
        return _to_out(db.scalars(stmt).all())


def fetch_records_by_keyword(issue_keyword: str, equipment_id: str | None = None) -> list[ServiceRecordOut]:
    issue_keyword = KeywordInput(issue_keyword=issue_keyword).issue_keyword
    pattern = f"%{issue_keyword}%"
    # "overheating" should also match "overheat"/"overheated" in descriptions
    stem = issue_keyword[:-3] if issue_keyword.lower().endswith("ing") and len(issue_keyword) > 5 else issue_keyword
    stem_pattern = f"%{stem}%"
    stmt = select(ServiceRecord).where(or_(
        ServiceRecord.issue_description.ilike(stem_pattern),
        ServiceRecord.diagnosis.ilike(stem_pattern),
        ServiceRecord.resolution.ilike(stem_pattern),
        ServiceRecord.error_code.ilike(pattern),
    ))
    if equipment_id:
        stmt = stmt.where(ServiceRecord.equipment_id == EquipmentIdInput(equipment_id=equipment_id).equipment_id)
    stmt = stmt.order_by(desc(ServiceRecord.service_date))
    with get_sessionmaker()() as db:
        return _to_out(db.scalars(stmt).all())


def search_manual_chunks(query: str) -> list[Citation]:
    return retrieve(ManualQueryInput(query=query).query)


# LangChain tool wrappers (name, description, and arg schema are what an LLM sees).
@tool("search_manuals", args_schema=ManualQueryInput)
def search_manuals(query: str) -> list[dict]:
    """Semantic search over uploaded equipment manuals. Returns text excerpts with document name and page."""
    return [c.model_dump() for c in search_manual_chunks(query)]


@tool("get_service_history", args_schema=EquipmentIdInput)
def get_service_history(equipment_id: str) -> list[dict]:
    """Return all service records for one machine, newest first."""
    return [r.model_dump(mode="json") for r in fetch_service_history(equipment_id)]


@tool("search_service_records", args_schema=KeywordInput)
def search_service_records(issue_keyword: str) -> list[dict]:
    """Search all service records for an issue keyword or error code."""
    return [r.model_dump(mode="json") for r in fetch_records_by_keyword(issue_keyword)]


ALL_TOOLS = [search_manuals, get_service_history, search_service_records]
