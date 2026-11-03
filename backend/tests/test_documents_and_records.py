"""API tests for document ingestion and service-record endpoints."""
import io

import pytest
from pydantic import ValidationError

from app.tools import fetch_records_by_keyword, fetch_service_history


def test_upload_indexes_pages(uploaded_manual):
    assert uploaded_manual["status"] == "ready"
    assert uploaded_manual["num_pages"] == 5
    assert uploaded_manual["num_chunks"] >= 5


def test_duplicate_upload_rejected(client, uploaded_manual):
    from tests.conftest import SAMPLE_PDF
    r = client.post("/api/documents/upload", files={"file": ("copy.pdf", SAMPLE_PDF.read_bytes(), "application/pdf")})
    assert r.status_code == 409


@pytest.mark.parametrize("name,content", [
    ("notes.txt", b"hello"),            # wrong extension
    ("fake.pdf", b"not really a pdf"),  # wrong magic bytes
    ("broken.pdf", b"%PDF-1.4 garbage"),  # corrupted
    ("empty.pdf", b""),
])
def test_invalid_upload_rejected(client, name, content):
    r = client.post("/api/documents/upload", files={"file": (name, io.BytesIO(content), "application/pdf")})
    assert r.status_code == 400, r.text


def test_list_and_delete_document(client):
    import pymupdf
    pdf = pymupdf.open()
    pdf.new_page().insert_text((72, 72), "Temporary test document about pallet changers.")
    data = pdf.tobytes()
    created = client.post("/api/documents/upload", files={"file": ("temp.pdf", data, "application/pdf")}).json()
    assert any(d["id"] == created["id"] for d in client.get("/api/documents").json())
    assert client.delete(f"/api/documents/{created['id']}").status_code == 204
    assert client.delete(f"/api/documents/{created['id']}").status_code == 404
    assert all(d["id"] != created["id"] for d in client.get("/api/documents").json())


def test_service_history_tool_returns_db_rows(client):
    records = fetch_service_history("m-102")  # normalised to upper case
    assert [r.service_id for r in records] == ["SR-1012", "SR-1008", "SR-1003", "SR-1001"]  # newest first


def test_keyword_tool(client):
    ids = {r.service_id for r in fetch_records_by_keyword("overheating")}
    assert ids == {"SR-1001", "SR-1003", "SR-1007"}
    assert {r.service_id for r in fetch_records_by_keyword("E104", "M-102")} == {"SR-1001", "SR-1003", "SR-1012"}


@pytest.mark.parametrize("bad", ["M-102' OR '1'='1", "DROP TABLE", "", "M102; --"])
def test_tool_rejects_malicious_input(bad):
    with pytest.raises(ValidationError):
        fetch_service_history(bad)


def test_records_endpoints(client):
    assert len(client.get("/api/service-records").json()) == 12
    assert len(client.get("/api/service-records", params={"equipment_id": "M-103"}).json()) == 2
    assert client.get("/api/service-records/M-102").status_code == 200
    assert client.get("/api/service-records/M-999").status_code == 404
    assert client.get("/api/service-records/not valid").status_code == 422


def test_dashboard_stats(client, uploaded_manual):
    stats = client.get("/api/dashboard/stats").json()
    assert stats["total_documents"] >= 1
    assert stats["equipment_count"] == 6
    assert stats["service_record_count"] == 12
    assert len(stats["recent_incidents"]) == 5


def test_failed_upload_can_be_retried(client, monkeypatch):
    import pymupdf
    from app import ingestion
    pdf = pymupdf.open()
    pdf.new_page().insert_text((72, 72), "Retry test document for the spindle chiller.")
    data = pdf.tobytes()

    def boom(*a, **k):
        raise RuntimeError("embedding service down")
    monkeypatch.setattr(ingestion, "index_chunks", boom)
    r = client.post("/api/documents/upload", files={"file": ("retry.pdf", data, "application/pdf")})
    assert r.status_code == 502
    monkeypatch.undo()
    r = client.post("/api/documents/upload", files={"file": ("retry.pdf", data, "application/pdf")})
    assert r.status_code == 201 and r.json()["status"] == "ready"
    assert sum(d["filename"] == "retry.pdf" for d in client.get("/api/documents").json()) == 1
    client.delete(f"/api/documents/{r.json()['id']}")
