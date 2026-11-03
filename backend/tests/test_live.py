"""The five demo scenarios against the real Gemini API.

Run with:  RUN_LIVE=1 pytest tests/test_live.py -v -s
Requires GEMINI_API_KEY in backend/.env. Skipped otherwise.
"""
import re

import pytest

from app.config import get_settings
from tests.conftest import LIVE

pytestmark = [
    pytest.mark.skipif(not LIVE or not get_settings().llm_configured, reason="set RUN_LIVE=1 and GEMINI_API_KEY"),
    pytest.mark.usefixtures("uploaded_manual"),
]
MANUAL = "XYZ-200_Service_Manual.pdf"


def ask(client, q):
    r = client.post("/api/chat", json={"question": q})
    assert r.status_code == 200, r.text
    res = r.json()
    print(f"\nQ: {q}\nroute={res['route']} tools={res['tools_used']} sufficient={res['sufficient_evidence']}")
    print("citations:", [(c["document_name"], c["page"]) for c in res["citations"]])
    print("records:", [r["service_id"] for r in res["service_records"]])
    print("A:", res["answer"])
    assert not re.search(r"\[\s*D\d", res["answer"]), "raw [D#] label leaked to the user"
    return res


def test_live_1_pdf(client):
    res = ask(client, "Explain error code E104.")
    assert "search_manuals" in res["tools_used"] and res["sufficient_evidence"]
    assert any(c["document_name"] == MANUAL and c["page"] == 2 for c in res["citations"])


def test_live_2_history(client):
    res = ask(client, "Show service history for machine M-102.")
    assert "get_service_history" in res["tools_used"]
    assert {r["service_id"] for r in res["service_records"]} == {"SR-1001", "SR-1003", "SR-1008", "SR-1012"}


def test_live_3_both(client):
    res = ask(client, "Machine M-102 is overheating. What does the manual recommend, and has this happened before?")
    assert res["route"] == "both" and "search_manuals" in res["tools_used"] and "get_service_history" in res["tools_used"]
    assert any(c["page"] == 3 for c in res["citations"])
    assert {"SR-1001", "SR-1003"} <= {r["service_id"] for r in res["service_records"]}


def test_live_4_no_docs(client):
    res = ask(client, "What is the warranty period for the robotic welding arm?")
    assert res["sufficient_evidence"] is False


def test_live_5_no_record(client):
    res = ask(client, "Show service history for machine M-999.")
    assert res["service_records"] == [] and res["sufficient_evidence"] is False
