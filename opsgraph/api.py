"""FastAPI service: /ask, /graph/entity/{name}, /ingest, /health."""

from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from opsgraph import config
from opsgraph.flow import ask, build_flow
from opsgraph.graph import GraphDB, q_entity, q_entity_neighbours
from opsgraph.ingest import ingest
from opsgraph.llm import LLMClient
from opsgraph.retrieval import Retriever


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    retriever: Literal["auto", "vector", "graph", "hybrid"] = "auto"
    k: int = Field(default=5, ge=1, le=20)


class IngestRequest(BaseModel):
    extractor: Literal["rules", "llm"] = "rules"
    reset: bool = True


class AppState:
    """Shared resources, opened once at startup."""

    db: GraphDB
    retriever: Retriever


state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    state.db = GraphDB()
    state.retriever = Retriever(state.db)
    yield
    state.db.close()


app = FastAPI(title="OpsGraph", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def _build_flow():
    llm = LLMClient() if config.llm_configured() else None
    return build_flow(state.retriever, llm)


@app.get("/health")
def health() -> dict:
    ok = state.db.ping()
    llm_on = config.llm_configured()
    return {
        "status": "ok" if ok else "degraded",
        "neo4j": ok,
        "graph": state.db.counts() if ok else {},
        "llm_configured": llm_on,
        "llm_model": config.LLM_MODEL if llm_on else None,
        "embedding_model": config.EMBEDDING_MODEL,
    }


@app.post("/ask")
def ask_endpoint(req: AskRequest) -> dict:
    try:
        out = ask(_build_flow(), req.question, None if req.retriever == "auto" else req.retriever, req.k)
    except Exception as exc:  # surface model/DB failures as 502 instead of a stack trace
        raise HTTPException(502, f"query failed: {exc}") from exc
    res = out["result"]
    return {
        "question": req.question,
        "answer": out["answer"],
        "mode": out["mode"],
        "kind": out["kind"],
        "retriever": out["retriever"],
        "grounded": out["grounded"],
        "citations": [c.as_dict() for c in res.chunks],
        "cited_ids": out["citations"],
        "paths": [p.as_dict() for p in res.paths],
        "subgraph": state.retriever.subgraph(res),
        "trace": out["trace"],
    }


@app.get("/graph/entity/{name}")
def entity(name: str) -> dict:
    rows = state.db.run(*q_entity(name))
    if not rows:
        raise HTTPException(404, f"no entity matching {name!r}")
    found = rows[0]
    neighbours = state.db.run(*q_entity_neighbours(found["id"]))
    return {"id": found["id"], "type": found["type"], "properties": found["properties"], "neighbours": neighbours}


@app.post("/ingest")
def ingest_endpoint(req: IngestRequest) -> dict:
    try:
        stats = ingest(req.extractor, reset=req.reset, db=state.db)
    except Exception as exc:  # same reasoning as /ask
        raise HTTPException(502, f"ingest failed: {exc}") from exc
    return stats.as_dict()
