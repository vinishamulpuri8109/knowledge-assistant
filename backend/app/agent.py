"""LangGraph agent: route the question, call the right tools, synthesize a grounded answer.

    START -> router --(docs)--> retrieve_docs ---------> synthesize -> END
                    --(db)----> query_db -------------->
                    --(both)--> retrieve_docs + query_db (parallel) -->
                    --(none)--> synthesize
"""
import logging
import operator
import re
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select

from app.database import get_sessionmaker
from app.llm import LLMNotConfiguredError, get_chat_model
from app.models import ServiceRecord
from app.schemas import Citation, Route, ServiceRecordOut
from app.tools import (
    EQUIPMENT_ID_RE,
    EquipmentIdInput,
    KeywordInput,
    fetch_records_by_keyword,
    fetch_service_history,
    search_manual_chunks,
)

log = logging.getLogger(__name__)


class AgentState(TypedDict, total=False):
    question: str
    route: Route
    router_mode: str  # "llm" or "rules"
    equipment_id: str | None
    issue_keyword: str | None
    search_query: str
    citations: list[Citation]
    service_records: list[ServiceRecordOut]
    db_summary: str
    # Parallel branches both append to these, so they need a merge (reducer) function
    tools_used: Annotated[list[str], operator.add]
    errors: Annotated[list[str], operator.add]
    answer: str
    sufficient_evidence: bool


# ---------------------------------------------------------------- router
class RouteDecision(BaseModel):
    route: Literal["docs", "db", "both", "none"] = Field(description=(
        "docs = needs equipment manuals (procedures, error code meanings, troubleshooting, specs); "
        "db = needs service history records (past incidents, repairs, what happened to a machine); "
        "both = needs manuals AND service history; none = greeting or unrelated to equipment service"))
    equipment_id: str | None = Field(None, description="Specific machine ID like 'M-102' if mentioned, else null. Model names are NOT machine IDs.")
    issue_keyword: str | None = Field(None, description="Short issue keyword or error code to search records for, e.g. 'overheating' or 'E104', else null")
    search_query: str | None = Field(None, description="Concise query for searching the manuals, if route is docs or both")


ROUTER_PROMPT = """You route questions from manufacturing technicians to data sources.
Sources:
- Equipment manuals (PDFs): procedures, troubleshooting steps, error code meanings, maintenance, specifications.
- Service records database: past service incidents per machine (equipment IDs like M-101, M-102).
Known equipment MODEL names (these are not machine IDs): {models}.
Pick the minimal set of sources needed. Questions about whether something happened before, past repairs,
or a machine's history need the database. Questions about what to do, recommendations, or meanings need manuals."""

ISSUE_TERMS = ["overheating", "overheat", "vibration", "leak", "pressure", "noise", "jam", "misalignment",
               "temperature", "lubrication", "sensor", "emergency stop", "flicker", "coolant", "bearing"]
DB_SIGNALS = ["history", "previously", "before", "happened", "past", "record", "serviced", "incident",
              "experienced", "last time", "repairs", "how often"]
DOC_SIGNALS = ["manual", "explain", "how do i", "how to", "troubleshoot", "recommend", "procedure", "what does",
               "what is", "meaning", "steps", "maintenance", "specification", "should i", "fix", "error code"]


def known_models() -> set[str]:
    with get_sessionmaker()() as db:
        return {m.upper() for m in db.scalars(select(ServiceRecord.equipment_model).distinct())}


def extract_equipment_id(text: str, models: set[str]) -> str | None:
    for cand in re.findall(r"\b[A-Z]{1,4}-\d{1,6}\b", text.upper()):
        if cand not in models and EQUIPMENT_ID_RE.match(cand):
            return cand
    return None


def rule_based_route(question: str, models: set[str]) -> RouteDecision:
    """Deterministic fallback router (used when the LLM is unavailable)."""
    q = question.lower()
    equipment_id = extract_equipment_id(question, models)
    code = re.search(r"\bE\d{3}\b", question.upper())
    keyword = code.group(0) if code else next((t for t in ISSUE_TERMS if t in q), None)
    wants_db = any(s in q for s in DB_SIGNALS) or (equipment_id is not None and not any(s in q for s in DOC_SIGNALS))
    wants_docs = any(s in q for s in DOC_SIGNALS) or (keyword is not None and not wants_db)
    if wants_db and wants_docs:
        route = "both"
    elif wants_db:
        route = "db"
    elif wants_docs:
        route = "docs"
    else:
        route = "none"
    return RouteDecision(route=route, equipment_id=equipment_id, issue_keyword=keyword, search_query=question)


def router_node(state: AgentState) -> AgentState:
    question = state["question"]
    models = known_models()
    errors: list[str] = []
    try:
        llm = get_chat_model().with_structured_output(RouteDecision)
        decision: RouteDecision = llm.invoke([
            SystemMessage(ROUTER_PROMPT.format(models=", ".join(sorted(models)))),
            HumanMessage(question),
        ])
        mode = "llm"
    except Exception as exc:
        log.warning("LLM router failed (%s); using rule-based router", exc)
        decision, mode = rule_based_route(question, models), "rules"

    # Validate what the LLM extracted before any tool sees it
    equipment_id = decision.equipment_id
    if equipment_id:
        try:
            equipment_id = EquipmentIdInput(equipment_id=equipment_id).equipment_id
            if equipment_id in models:  # a model name, not a machine ID
                equipment_id = None
        except ValidationError:
            errors.append(f"Ignored invalid equipment ID '{decision.equipment_id}'.")
            equipment_id = None
    keyword = decision.issue_keyword
    if keyword:
        try:
            keyword = KeywordInput(issue_keyword=keyword).issue_keyword
        except ValidationError:
            errors.append(f"Ignored invalid issue keyword '{decision.issue_keyword}'.")
            keyword = None

    route = decision.route
    if route in ("db", "both") and not equipment_id and not keyword:
        # Nothing valid to query the database with
        route = "docs" if route == "both" else "none"
    return {
        "route": route, "router_mode": mode, "equipment_id": equipment_id, "issue_keyword": keyword,
        "search_query": decision.search_query or question, "errors": errors,
    }


def after_router(state: AgentState) -> list[str]:
    return {
        "docs": ["retrieve_docs"],
        "db": ["query_db"],
        "both": ["retrieve_docs", "query_db"],  # parallel fan-out
        "none": ["synthesize"],
    }[state["route"]]


# ---------------------------------------------------------------- tool nodes
def retrieve_docs_node(state: AgentState) -> AgentState:
    try:
        citations = search_manual_chunks(state["search_query"])
        return {"citations": citations, "tools_used": ["search_manuals"]}
    except LLMNotConfiguredError:
        raise  # surfaces as HTTP 503 instead of a misleading "no evidence" answer
    except Exception as exc:
        log.exception("search_manuals failed")
        return {"citations": [], "tools_used": ["search_manuals"], "errors": [f"Manual search failed: {exc}"]}


def query_db_node(state: AgentState) -> AgentState:
    equipment_id, keyword = state.get("equipment_id"), state.get("issue_keyword")
    tools, errors = [], []
    records: list[ServiceRecordOut] = []
    summary = ""
    try:
        if equipment_id:
            tools.append("get_service_history")
            history = fetch_service_history(equipment_id)
            if keyword:
                tools.append("search_service_records")
                matching_ids = {r.service_id for r in fetch_records_by_keyword(keyword, equipment_id)}
                records = [r for r in history if r.service_id in matching_ids]
                summary = (f"Machine {equipment_id} has {len(history)} service record(s) in total; "
                           f"{len(records)} match '{keyword}'.")
            else:
                records = history
                summary = f"Machine {equipment_id} has {len(history)} service record(s)."
        elif keyword:
            tools.append("search_service_records")
            records = fetch_records_by_keyword(keyword)
            summary = f"{len(records)} service record(s) across all machines match '{keyword}'."
    except Exception as exc:
        log.exception("database tool failed")
        errors.append(f"Service record lookup failed: {exc}")
    return {"service_records": records, "db_summary": summary, "tools_used": tools, "errors": errors}


# ---------------------------------------------------------------- synthesis
class GroundedAnswer(BaseModel):
    answer: str = Field(description="Answer for the technician. Cite manual excerpts inline as [D1], [D2]. Refer to service records by service ID (e.g. SR-1003) and date.")
    sufficient_evidence: bool = Field(description="True only if the provided context actually answers the question")
    cited_sources: list[str] = Field(default_factory=list, description="Labels of manual excerpts used, e.g. ['D1','D3']")


SYNTH_PROMPT = """You are a service assistant for manufacturing technicians.
Answer ONLY from the context below. Do not use outside knowledge about equipment.
If the context does not contain the answer, say clearly what is missing and set sufficient_evidence to false.
Be concise and practical: use short numbered steps for procedures.
When both manuals and service history are present, give the manual recommendation first, then summarize past incidents."""

GENERAL_PROMPT = """You are a service assistant for manufacturing technicians. The user's message does not need
manuals or service records. Reply briefly and explain you can answer questions about uploaded equipment manuals
and machine service history (e.g. 'Show service history for M-102')."""


def _build_context(state: AgentState) -> str:
    parts = []
    citations = state.get("citations") or []
    if state["route"] in ("docs", "both"):
        parts.append("## Manual excerpts")
        parts += [f"[D{i}] ({c.document_name}, page {c.page})\n{c.excerpt}" for i, c in enumerate(citations, 1)] or ["(no relevant manual excerpts found)"]
    if state["route"] in ("db", "both"):
        parts.append("## Service records")
        if state.get("db_summary"):
            parts.append(state["db_summary"])
        for r in state.get("service_records") or []:
            parts.append(f"- {r.service_id} | {r.service_date} | {r.equipment_id} ({r.equipment_model}) | issue: {r.issue_description} | "
                         f"error: {r.error_code or 'none'} | diagnosis: {r.diagnosis} | resolution: {r.resolution}")
    return "\n\n".join(parts)


def _no_evidence_message(state: AgentState) -> str:
    searched, hints = [], []
    if state["route"] in ("docs", "both"):
        searched.append("the uploaded manuals")
        hints.append("upload the manual that covers this topic")
    if state["route"] in ("db", "both"):
        target = state.get("equipment_id") or f"'{state.get('issue_keyword')}'"
        searched.append(f"service records for {target}")
        hints.append("check that the equipment ID is correct")
    return ("I could not find sufficient supporting evidence to answer this. I searched "
            + " and ".join(searched) + " but found no relevant information. "
            + "Try to " + " or ".join(hints) + ".")


LABEL_GROUP_RE = re.compile(r"\[\s*D\d+(?:\s*[,;]\s*D\d+)*\s*\]")  # [D1], [D1, D2], [D1; D3]


def renumber_citations(answer: str, cited_sources: list[str], num_retrieved: int) -> tuple[str, list[int]]:
    """Keep only labels that point at retrieved chunks, and renumber them [D3] -> [1]
    to match the order of the returned citation list. Returns (answer, used chunk indexes)."""
    used: list[int] = []
    labels = cited_sources + [l for g in LABEL_GROUP_RE.findall(answer) for l in re.findall(r"D\d+", g)]
    for label in labels:
        m = re.fullmatch(r"\[?D(\d+)\]?", label.strip())
        idx = int(m.group(1)) - 1 if m else -1
        if 0 <= idx < num_retrieved and idx not in used:
            used.append(idx)
    renumber = {idx: n for n, idx in enumerate(used, 1)}

    def replace(group: re.Match) -> str:
        nums = sorted({renumber[int(d) - 1] for d in re.findall(r"D(\d+)", group.group(0)) if int(d) - 1 in renumber})
        return f"[{', '.join(map(str, nums))}]" if nums else ""

    return LABEL_GROUP_RE.sub(replace, answer).strip(), used


def synthesize_node(state: AgentState) -> AgentState:
    route = state["route"]
    citations = state.get("citations") or []
    records = state.get("service_records") or []

    if route == "none":
        reply = get_chat_model().invoke([SystemMessage(GENERAL_PROMPT), HumanMessage(state["question"])])
        return {"answer": reply.text, "sufficient_evidence": False, "citations": []}

    if not citations and not records:
        # Guardrail: never let the LLM answer from thin air
        return {"answer": _no_evidence_message(state), "sufficient_evidence": False, "citations": []}

    llm = get_chat_model().with_structured_output(GroundedAnswer)
    result: GroundedAnswer = llm.invoke([
        SystemMessage(SYNTH_PROMPT),
        HumanMessage(f"Question: {state['question']}\n\n{_build_context(state)}"),
    ])

    answer, used = renumber_citations(result.answer, result.cited_sources, len(citations))
    return {
        "answer": answer,
        # The model's own judgement must also be backed by something we can show the user
        "sufficient_evidence": result.sufficient_evidence and bool(used or records),
        "citations": [citations[i] for i in used],
    }


# ---------------------------------------------------------------- graph
def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("router", router_node)
    graph.add_node("retrieve_docs", retrieve_docs_node)
    graph.add_node("query_db", query_db_node)
    graph.add_node("synthesize", synthesize_node)

    graph.add_edge(START, "router")
    graph.add_conditional_edges("router", after_router, ["retrieve_docs", "query_db", "synthesize"])
    graph.add_edge("retrieve_docs", "synthesize")
    graph.add_edge("query_db", "synthesize")
    graph.add_edge("synthesize", END)
    return graph.compile()


_graph = None


def run_agent(question: str) -> AgentState:
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph.invoke({"question": question, "tools_used": [], "errors": []})
