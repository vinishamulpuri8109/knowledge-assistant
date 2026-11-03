"""Test setup. Every test session gets fresh temp storage (SQLite, Chroma, uploads).

Offline mode (default): Gemini is replaced by deterministic fakes so tests run without an API key.
Live mode (RUN_LIVE=1): real Gemini embeddings and chat model are used.
"""
import hashlib
import math
import os
import re
import tempfile
from pathlib import Path

import pytest

LIVE = os.environ.get("RUN_LIVE") == "1"
_tmp = Path(tempfile.mkdtemp(prefix="msa-test-"))
os.environ["SQLITE_PATH"] = str(_tmp / "test.db")
os.environ["CHROMA_DIR"] = str(_tmp / "chroma")
os.environ["UPLOAD_DIR"] = str(_tmp / "uploads")
if not LIVE:
    os.environ["GEMINI_API_KEY"] = ""          # never hit the network offline
    os.environ["RETRIEVAL_MAX_DISTANCE"] = "0.9"  # calibrated for the fake embedding below

from fastapi.testclient import TestClient  # noqa: E402
from langchain_core.embeddings import Embeddings  # noqa: E402

from app import agent, llm  # noqa: E402
from app.main import app  # noqa: E402

SAMPLE_PDF = Path(__file__).resolve().parents[2] / "sample_data" / "manuals" / "XYZ-200_Service_Manual.pdf"
STOPWORDS = set("a an the is are do does i in of for to and or what how has this be it on with my me".split())


class BagOfWordsEmbeddings(Embeddings):
    """Deterministic offline embedding: hashed word counts, L2-normalised.
    Texts that share words get similar vectors, which is enough to test retrieval logic."""

    dim = 512

    def _embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            if word in STOPWORDS:
                continue
            word = re.sub(r"(ing|ed|s)$", "", word) if len(word) > 4 else word
            vec[int(hashlib.md5(word.encode()).hexdigest(), 16) % self.dim] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts):
        return [self._embed(t) for t in texts]

    def embed_query(self, text):
        return self._embed(text)


class _FakeStructured:
    def __init__(self, parent, schema):
        self.parent, self.schema = parent, schema

    def invoke(self, messages):
        if self.schema is agent.RouteDecision:
            raise RuntimeError("offline: use rule-based router")
        context = messages[-1].content
        self.parent.contexts.append(context)
        labels = re.findall(r"\[(D\d+)\]", context)[:2]
        records = re.findall(r"SR-\d{4}", context)
        answer = "Grounded answer. " + " ".join(f"[{l}]" for l in labels) + (" Records: " + ", ".join(records) if records else "")
        return agent.GroundedAnswer(answer=answer, sufficient_evidence=bool(labels or records), cited_sources=labels)


class FakeChatModel:
    """Test double for Gemini. Records every prompt context it receives."""

    def __init__(self):
        self.contexts: list[str] = []

    def with_structured_output(self, schema):
        return _FakeStructured(self, schema)

    def invoke(self, messages):
        class _Reply:
            text = "I can help with equipment manuals and service history."
        return _Reply()


@pytest.fixture(scope="session")
def fake_llm():
    return FakeChatModel()


@pytest.fixture(scope="session")
def client(fake_llm):
    if not LIVE:
        llm.set_embeddings_override(BagOfWordsEmbeddings())
        agent.get_chat_model = lambda: fake_llm
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def uploaded_manual(client):
    with open(SAMPLE_PDF, "rb") as f:
        r = client.post("/api/documents/upload", files={"file": (SAMPLE_PDF.name, f, "application/pdf")})
    assert r.status_code == 201, r.text
    return r.json()
