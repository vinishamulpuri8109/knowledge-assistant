"""Retrieval: embed the question, query ChromaDB, keep only sufficiently similar chunks."""
from app.config import get_settings
from app.ingestion import get_collection
from app.llm import get_embeddings
from app.schemas import Citation


def retrieve(query: str, k: int | None = None) -> list[Citation]:
    """Return the top-k chunks whose cosine distance is within the relevance threshold."""
    settings = get_settings()
    collection = get_collection()
    if collection.count() == 0:
        return []
    vector = get_embeddings().embed_query(query)
    result = collection.query(
        query_embeddings=[vector],
        n_results=min(k or settings.top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )
    hits = []
    for text, meta, dist in zip(result["documents"][0], result["metadatas"][0], result["distances"][0]):
        if dist <= settings.retrieval_max_distance:
            hits.append(Citation(
                document_id=meta["document_id"], document_name=meta["document_name"],
                page=int(meta["page"]), excerpt=text, distance=round(float(dist), 4),
            ))
    return hits
