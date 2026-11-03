"""The five required demo scenarios, run through the real LangGraph agent via POST /api/chat.
Offline, the chat model is a test double, but routing rules, retrieval, SQL tools,
guardrails and citation filtering are all the real implementation."""
import pytest

from app.agent import known_models, rule_based_route

pytestmark = pytest.mark.usefixtures("uploaded_manual")
MANUAL = "XYZ-200_Service_Manual.pdf"


def ask(client, q):
    r = client.post("/api/chat", json={"question": q})
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.parametrize("question,route,equipment_id,keyword", [
    ("Explain error code E104.", "docs", None, "E104"),
    ("How do I troubleshoot overheating in XYZ-200?", "docs", None, "overheating"),
    ("Show service history for machine M-102.", "db", "M-102", None),
    ("Has machine M-102 previously experienced overheating?", "db", "M-102", "overheating"),
    ("Machine M-102 is overheating. What does the manual recommend, and has this happened before?", "both", "M-102", "overheating"),
    ("Hello there", "none", None, None),
])
def test_rule_router(client, question, route, equipment_id, keyword):
    d = rule_based_route(question, known_models())
    assert (d.route, d.equipment_id, d.issue_keyword) == (route, equipment_id, keyword)


def test_scenario_1_answer_from_pdf(client):
    res = ask(client, "Explain error code E104.")
    assert res["route"] == "docs" and res["tools_used"] == ["search_manuals"]
    assert res["sufficient_evidence"] is True
    assert res["citations"], "expected manual citations"
    top = res["citations"][0]
    assert top["document_name"] == MANUAL
    assert top["page"] == 2 and "E104" in top["excerpt"]  # error codes live on page 2


def test_scenario_2_service_history(client, fake_llm):
    res = ask(client, "Show service history for machine M-102.")
    assert res["route"] == "db" and res["tools_used"] == ["get_service_history"]
    assert [r["service_id"] for r in res["service_records"]] == ["SR-1012", "SR-1008", "SR-1003", "SR-1001"]
    assert "SR-1003" in fake_llm.contexts[-1]  # real DB rows were given to the LLM
    assert res["citations"] == []


def test_scenario_3_docs_and_db(client, fake_llm):
    res = ask(client, "Machine M-102 is overheating. What does the manual recommend, and has this happened before?")
    assert res["route"] == "both"
    assert set(res["tools_used"]) == {"search_manuals", "get_service_history", "search_service_records"}
    assert {r["service_id"] for r in res["service_records"]} == {"SR-1001", "SR-1003"}
    assert any(c["page"] == 3 for c in res["citations"])  # overheating procedure page
    assert "[D" not in res["answer"]  # labels renumbered for the UI
    ctx = fake_llm.contexts[-1]
    assert "## Manual excerpts" in ctx and "## Service records" in ctx


def test_scenario_4_no_supporting_docs(client, fake_llm):
    calls_before = len(fake_llm.contexts)
    res = ask(client, "What is the warranty period for the robotic welding arm?")
    assert res["route"] == "docs"
    assert res["citations"] == [] and res["sufficient_evidence"] is False
    assert "could not find sufficient supporting evidence" in res["answer"]
    assert len(fake_llm.contexts) == calls_before  # guardrail: LLM not asked to answer without evidence


def test_scenario_5_no_matching_service_record(client):
    res = ask(client, "Show service history for machine M-999.")
    assert res["route"] == "db" and res["tools_used"] == ["get_service_history"]
    assert res["service_records"] == [] and res["sufficient_evidence"] is False
    assert "M-999" in res["answer"]


def test_chat_validation(client):
    assert client.post("/api/chat", json={"question": ""}).status_code == 422


def test_recent_queries_logged(client):
    ask(client, "Show service history for machine M-101.")
    recent = client.get("/api/dashboard/stats").json()["recent_queries"]
    assert recent[0]["question"] == "Show service history for machine M-101."


@pytest.mark.parametrize("answer,cited,expected,used", [
    ("A [D3]. B [D1].", [], "A [1]. B [2].", [2, 0]),
    ("Restart [D1, D2].", [], "Restart [1, 2].", [0, 1]),
    ("Mixed [D2; D1] and [D9].", [], "Mixed [1, 2] and .", [1, 0]),  # D9 was never retrieved -> dropped
    ("No labels.", ["D2"], "No labels.", [1]),
])
def test_renumber_citations(answer, cited, expected, used):
    from app.agent import renumber_citations
    assert renumber_citations(answer, cited, num_retrieved=3) == (expected, used)
