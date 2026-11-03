from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app import services
from app.database import get_db
from app.ingestion import InvalidDocumentError
from app.schemas import DocumentOut

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    data = await file.read()
    try:
        doc = services.upload_document(db, file.filename or "upload.pdf", data)
    except InvalidDocumentError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    except services.DuplicateDocumentError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Duplicate of already uploaded '{exc.existing.filename}'.")
    if doc.status == "failed":
        code = status.HTTP_503_SERVICE_UNAVAILABLE if "GEMINI_API_KEY" in (doc.error or "") else status.HTTP_502_BAD_GATEWAY
        raise HTTPException(code, f"Document saved but indexing failed: {doc.error}")
    return doc


@router.get("", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db)):
    return services.list_documents(db)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str, db: Session = Depends(get_db)):
    if not services.delete_document(db, document_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
