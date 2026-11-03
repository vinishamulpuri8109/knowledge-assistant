import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import services
from app.database import get_db
from app.llm import LLMNotConfiguredError
from app.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/api", tags=["chat"])
log = logging.getLogger(__name__)


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        return services.answer_question(db, request.question.strip())
    except LLMNotConfiguredError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))
    except Exception as exc:
        log.exception("chat failed")
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"The AI service failed to answer: {exc}")
