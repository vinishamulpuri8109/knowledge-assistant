"""Factories for the Gemini chat model and embedding model.

Kept in one place so tests can swap in offline fakes via `set_embeddings_override`.
"""
from functools import lru_cache

from langchain_core.embeddings import Embeddings

from app.config import get_settings


class LLMNotConfiguredError(RuntimeError):
    """Raised when GEMINI_API_KEY is missing."""


_embeddings_override: Embeddings | None = None


def set_embeddings_override(embeddings: Embeddings | None) -> None:
    global _embeddings_override
    _embeddings_override = embeddings


def _require_key() -> str:
    settings = get_settings()
    if not settings.llm_configured:
        raise LLMNotConfiguredError("GEMINI_API_KEY is not set. Copy backend/.env.example to backend/.env and add your key.")
    return settings.gemini_api_key


def get_embeddings() -> Embeddings:
    if _embeddings_override is not None:
        return _embeddings_override
    return _gemini_embeddings(_require_key())


@lru_cache
def _gemini_embeddings(api_key: str):
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    return GoogleGenerativeAIEmbeddings(model=get_settings().gemini_embedding_model, google_api_key=api_key)


def get_chat_model():
    return _gemini_chat(_require_key())


@lru_cache
def _gemini_chat(api_key: str):
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(model=get_settings().gemini_chat_model, google_api_key=api_key, temperature=0)
