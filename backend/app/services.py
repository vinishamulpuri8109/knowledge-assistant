"""Business logic shared by the API routes (documents, chat logging, dashboard)."""
import uuid

from sqlalchemy import desc, distinct, func, select
from sqlalchemy.orm import Session

from app import ingestion
from app.agent import run_agent
from app.config import get_settings
from app.models import Document, QueryLog, ServiceRecord
from app.schemas import ChatResponse, DashboardStats, RecentQuery, ServiceRecordOut


class DuplicateDocumentError(Exception):
    def __init__(self, existing: Document):
        self.existing = existing


def upload_document(db: Session, filename: str, data: bytes) -> Document:
    ingestion.validate_pdf(filename, data)  # fail fast before touching the DB
    file_hash = ingestion.file_sha256(data)
    existing = db.scalar(select(Document).where(Document.file_hash == file_hash))
    if existing and existing.status == "failed":
        delete_document(db, existing.id)  # allow retrying a previously failed upload
    elif existing:
        raise DuplicateDocumentError(existing)

    doc = Document(id=str(uuid.uuid4()), filename=filename, file_hash=file_hash, status="processing")
    db.add(doc)
    db.commit()
    try:
        doc.num_pages, doc.num_chunks = ingestion.ingest_pdf(doc.id, filename, data)
        (get_settings().upload_dir / f"{doc.id}.pdf").write_bytes(data)
        doc.status = "ready"
    except ingestion.InvalidDocumentError:
        db.delete(doc)
        db.commit()
        raise
    except Exception as exc:
        doc.status, doc.error = "failed", str(exc)[:500]
    db.commit()
    return doc


def list_documents(db: Session) -> list[Document]:
    return list(db.scalars(select(Document).order_by(desc(Document.uploaded_at))))


def delete_document(db: Session, document_id: str) -> bool:
    doc = db.get(Document, document_id)
    if not doc:
        return False
    ingestion.delete_document_chunks(document_id)
    (get_settings().upload_dir / f"{document_id}.pdf").unlink(missing_ok=True)
    db.delete(doc)
    db.commit()
    return True


def answer_question(db: Session, question: str) -> ChatResponse:
    state = run_agent(question)
    response = ChatResponse(
        answer=state["answer"],
        citations=state.get("citations") or [],
        service_records=state.get("service_records") or [],
        tools_used=list(dict.fromkeys(state.get("tools_used") or [])),
        route=state["route"],
        sufficient_evidence=state.get("sufficient_evidence", False),
        errors=state.get("errors") or [],
    )
    db.add(QueryLog(question=question, route=response.route, tools_used=",".join(response.tools_used),
                    sufficient_evidence=response.sufficient_evidence))
    db.commit()
    return response


def dashboard_stats(db: Session) -> DashboardStats:
    return DashboardStats(
        total_documents=db.scalar(select(func.count()).select_from(Document)) or 0,
        ready_documents=db.scalar(select(func.count()).select_from(Document).where(Document.status == "ready")) or 0,
        total_chunks=db.scalar(select(func.coalesce(func.sum(Document.num_chunks), 0))) or 0,
        equipment_count=db.scalar(select(func.count(distinct(ServiceRecord.equipment_id)))) or 0,
        service_record_count=db.scalar(select(func.count()).select_from(ServiceRecord)) or 0,
        recent_queries=[RecentQuery.model_validate(q) for q in
                        db.scalars(select(QueryLog).order_by(desc(QueryLog.created_at)).limit(5))],
        recent_incidents=[ServiceRecordOut.model_validate(r) for r in
                          db.scalars(select(ServiceRecord).order_by(desc(ServiceRecord.service_date)).limit(5))],
        llm_configured=get_settings().llm_configured,
    )
