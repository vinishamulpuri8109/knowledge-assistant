"""PDF ingestion: validate -> extract text per page -> chunk -> embed -> store in ChromaDB."""
import hashlib
from dataclasses import dataclass
from functools import lru_cache

import chromadb
import pymupdf
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import get_settings
from app.llm import get_embeddings

COLLECTION_NAME = "equipment_manuals"
EMBED_BATCH_SIZE = 50


class InvalidDocumentError(ValueError):
    """The uploaded file is not a usable PDF."""


@dataclass
class Chunk:
    id: str
    text: str
    page: int  # 1-based page number


@lru_cache
def get_collection():
    client = chromadb.PersistentClient(path=str(get_settings().chroma_dir))
    # We always pass our own embeddings, so no Chroma embedding function is needed.
    return client.get_or_create_collection(
        COLLECTION_NAME, embedding_function=None, metadata={"hnsw:space": "cosine"}
    )


def file_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_pdf(filename: str, data: bytes) -> None:
    settings = get_settings()
    if not filename.lower().endswith(".pdf"):
        raise InvalidDocumentError("Only .pdf files are supported.")
    if not data:
        raise InvalidDocumentError("The uploaded file is empty.")
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise InvalidDocumentError(f"File exceeds the {settings.max_upload_mb} MB limit.")
    if not data.startswith(b"%PDF"):
        raise InvalidDocumentError("File content is not a valid PDF.")


def extract_pages(data: bytes) -> list[tuple[int, str]]:
    """Return [(page_number, text)] for pages that contain text."""
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:  # corrupted or encrypted file
        raise InvalidDocumentError(f"Could not open PDF: {exc}") from exc
    with doc:
        if doc.needs_pass:
            raise InvalidDocumentError("Password-protected PDFs are not supported.")
        pages = [(i + 1, page.get_text("text").strip()) for i, page in enumerate(doc)]
    pages = [(n, t) for n, t in pages if t]
    if not pages:
        raise InvalidDocumentError("No extractable text found (the PDF may be scanned images).")
    return pages


def chunk_pages(document_id: str, pages: list[tuple[int, str]]) -> list[Chunk]:
    """Split each page separately so every chunk maps to exactly one page."""
    settings = get_settings()
    splitter = RecursiveCharacterTextSplitter(chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap)
    chunks: list[Chunk] = []
    for page_num, text in pages:
        for i, piece in enumerate(splitter.split_text(text)):
            chunks.append(Chunk(id=f"{document_id}:p{page_num}:c{i}", text=piece, page=page_num))
    return chunks


def index_chunks(document_id: str, document_name: str, chunks: list[Chunk]) -> None:
    embeddings = get_embeddings()
    collection = get_collection()
    for start in range(0, len(chunks), EMBED_BATCH_SIZE):
        batch = chunks[start : start + EMBED_BATCH_SIZE]
        vectors = embeddings.embed_documents([c.text for c in batch])
        collection.add(
            ids=[c.id for c in batch],
            embeddings=vectors,
            documents=[c.text for c in batch],
            metadatas=[{"document_id": document_id, "document_name": document_name, "page": c.page} for c in batch],
        )


def delete_document_chunks(document_id: str) -> None:
    get_collection().delete(where={"document_id": document_id})


def ingest_pdf(document_id: str, filename: str, data: bytes) -> tuple[int, int]:
    """Full pipeline. Returns (num_pages, num_chunks). Raises InvalidDocumentError on bad input."""
    validate_pdf(filename, data)
    pages = extract_pages(data)
    chunks = chunk_pages(document_id, pages)
    try:
        index_chunks(document_id, filename, chunks)
    except Exception:
        delete_document_chunks(document_id)  # don't leave a half-indexed document behind
        raise
    return len(pages), len(chunks)
