"""FastAPI entry point. Run with: uvicorn app.main:app --reload"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.routes import chat, documents, records

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Mini Enterprise Service Assistant", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_origins, allow_methods=["*"], allow_headers=["*"])
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(records.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "llm_configured": get_settings().llm_configured}
