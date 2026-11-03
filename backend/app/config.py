"""Application settings, loaded from environment variables / .env."""
from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    # Accept either GEMINI_API_KEY or GOOGLE_API_KEY
    gemini_api_key: str = Field(default="", validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_API_KEY"))
    gemini_chat_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "models/gemini-embedding-001"

    sqlite_path: Path = PROJECT_DIR / "sample_data" / "service_records.db"
    chroma_dir: Path = BACKEND_DIR / "data" / "chroma"
    upload_dir: Path = BACKEND_DIR / "data" / "uploads"

    chunk_size: int = 1000
    chunk_overlap: int = 150
    top_k: int = 5
    retrieval_max_distance: float = 0.35
    max_upload_mb: int = 20

    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @property
    def llm_configured(self) -> bool:
        return bool(self.gemini_api_key) and self.gemini_api_key != "your-gemini-api-key-here"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.chroma_dir.mkdir(parents=True, exist_ok=True)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    return settings
