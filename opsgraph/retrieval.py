"""Three retrievers over the same graph: vector-only, graph-augmented, hybrid (RRF)."""

import re
from dataclasses import dataclass, field
from itertools import combinations

from opsgraph import config
from opsgraph.embeddings import get_embedder
from opsgraph.graph import (
    GraphDB,
    q_chunk_vector_search,
    q_chunks_of_docs,
    q_expand,
    q_is_document,
    q_link_entities,
    q_nodes_edges,
    q_shortest_path,
)
from opsgraph.schema import INTENTS

RETRIEVERS = ("vector", "graph", "hybrid")


def unique(items: list[str]) -> list[str]:
    """Remove duplicates, keeping first-seen order."""
    return list(dict.fromkeys(items))


@dataclass
class RetrievedChunk:
    chunk_id: str
    doc_id: str
    text: str
    score: float
    via: str = "vector"  # vector | graph | both

    def as_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "text": self.text,
            "score": round(self.score, 4),
            "via": self.via,
        }


@dataclass
class GraphPath:
    node_ids: list[str]
    edges: list[dict]

    def describe(self) -> str:
        if not self.edges:
            return " ".join(self.node_ids)
        parts = [self.node_ids[0]]
        for e, nxt in zip(self.edges, self.node_ids[1:], strict=False):
            arrow = f"-[{e['type']}]->" if e["target"] == nxt else f"<-[{e['type']}]-"
            parts += [arrow, nxt]
        return " ".join(parts)

    def as_dict(self) -> dict:
        return {"nodes": self.node_ids, "edges": self.edges, "text": self.describe()}


@dataclass
class RetrievalResult:
    retriever: str
    chunks: list[RetrievedChunk]
    paths: list[GraphPath] = field(default_factory=list)
    seeds: list[str] = field(default_factory=list)

    def doc_ids(self) -> list[str]:
        """Documents of the retrieved chunks, in rank order."""
        return unique([c.doc_id for c in self.chunks])


def intent_types(question: str) -> set[str]:
    """Document types the question asks for, e.g. {"Rota"} for "who do I page for checkout-api?"."""
    return {doc_type for pattern, doc_type in INTENTS if re.search(pattern, question, re.I)}


class Retriever:
    def __init__(self, db: GraphDB | None = None):
        self.db = db or GraphDB()
        self.embedder = get_embedder()

    def _embed(self, question: str, embedding: list[float] | None) -> list[float]:
        return embedding or self.embedder.get_query_embedding(question)

    # -- vector ----------------------------------------------------------------------
    def vector(self, question: str, k: int | None = None, embedding: list[float] | None = None) -> RetrievalResult:
        k = k or config.TOP_K
        emb = self._embed(question, embedding)
        rows = self.db.run(*q_chunk_vector_search(k, emb))
        chunks = [RetrievedChunk(r["chunk_id"], r["doc_id"], r["text"], float(r["score"])) for r in rows]
        return RetrievalResult("vector", chunks)

    # -- graph-augmented ---------------------------------------------------------------
    def graph(self, question: str, k: int | None = None, embedding: list[float] | None = None) -> RetrievalResult:
        """Vector seeds + entity linking, then Cypher neighbourhood expansion and path queries."""
        k = k or config.TOP_K
        emb = self._embed(question, embedding)
        seed_chunks = self.db.run(*q_chunk_vector_search(config.SEED_K, emb))
        seed_docs = unique([r["doc_id"] for r in seed_chunks])
        linked = [r["id"] for r in self.db.run(*q_link_entities(question))]
        seeds = unique(linked + seed_docs)

        hops: dict[str, int] = {d: 0 for d in seed_docs}
        paths: dict[str, GraphPath] = {}
        if seeds:
            for r in self.db.run(*q_expand(config.MAX_HOPS, seeds)):
                d = r["doc_id"]
                if d not in paths or len(r["edges"]) < len(paths[d].edges):
                    paths[d] = GraphPath(r["node_ids"], r["edges"])
                if d not in hops:
                    hops[d] = r["hops"]
        for d in linked:  # documents named in the question are always candidates
            if d not in hops and self._is_doc(d):
                hops[d] = 0

        path_list: list[GraphPath] = []
        for a, b in list(combinations(linked, 2))[: config.MAX_ENTITY_PAIRS]:
            for r in self.db.run(*q_shortest_path(a, b, config.MAX_HOPS)):
                path_list.append(GraphPath(r["node_ids"], r["edges"]))
                for n in r["node_ids"]:
                    if self._is_doc(n):
                        hops[n] = 0

        wanted = intent_types(question)
        scored: list[RetrievedChunk] = []
        for r in self.db.run(*q_chunks_of_docs(list(hops), emb)):
            score = float(r["score"]) * config.HOP_DECAY ** hops[r["doc_id"]]
            if r["doc_type"] in wanted:
                score *= config.INTENT_BOOST
            # Edges are read from each document's metadata block, so for a document reached through
            # the graph the header chunk is the evidence for the hop (owner, on-call names, links).
            if hops[r["doc_id"]] > 0 and r["chunk_id"].endswith("#0.0"):
                score *= config.HEADER_BOOST
            scored.append(RetrievedChunk(r["chunk_id"], r["doc_id"], r["text"], score, "graph"))
        scored.sort(key=lambda c: c.score, reverse=True)
        top = self._diversify(scored, k)
        used_paths = [paths[c.doc_id] for c in top if c.doc_id in paths and paths[c.doc_id].edges]
        uniq = {p.describe(): p for p in used_paths + path_list}
        shown = sorted(uniq.values(), key=lambda p: len(p.edges))[: config.MAX_PATHS_SHOWN]
        return RetrievalResult("graph", top, shown, seeds)

    @staticmethod
    def _diversify(ranked: list[RetrievedChunk], k: int) -> list[RetrievedChunk]:
        """Best chunk of each document first, then the remaining chunks by score."""
        firsts, rest, seen = [], [], set()
        for c in ranked:
            (rest if c.doc_id in seen else firsts).append(c)
            seen.add(c.doc_id)
        return (firsts + rest)[:k] if len(firsts) < k else firsts[:k]

    def _is_doc(self, entity_id: str) -> bool:
        rows = self.db.run(*q_is_document(entity_id))
        return bool(rows and rows[0]["is_doc"])

    # -- hybrid ------------------------------------------------------------------------
    def hybrid(self, question: str, k: int | None = None, embedding: list[float] | None = None) -> RetrievalResult:
        """Reciprocal rank fusion of the vector and graph rankings."""
        k = k or config.TOP_K
        emb = self._embed(question, embedding)
        v = self.vector(question, k * 2, emb)
        g = self.graph(question, k * 2, emb)
        fused: dict[str, float] = {}
        by_id: dict[str, RetrievedChunk] = {}
        origin: dict[str, set[str]] = {}
        for name, res in (("vector", v), ("graph", g)):
            for rank, c in enumerate(res.chunks):
                fused[c.chunk_id] = fused.get(c.chunk_id, 0.0) + 1.0 / (config.RRF_K + rank + 1)
                by_id.setdefault(c.chunk_id, c)
                origin.setdefault(c.chunk_id, set()).add(name)
        ranked = sorted(fused, key=fused.get, reverse=True)[:k]  # type: ignore[arg-type]
        chunks = []
        for cid in ranked:
            c = by_id[cid]
            via = "both" if len(origin[cid]) == 2 else next(iter(origin[cid]))
            chunks.append(RetrievedChunk(cid, c.doc_id, c.text, fused[cid], via))
        return RetrievalResult("hybrid", chunks, g.paths, g.seeds)

    def retrieve(self, question: str, retriever: str = "hybrid", k: int | None = None) -> RetrievalResult:
        if retriever not in RETRIEVERS:
            raise ValueError(f"unknown retriever {retriever!r}; choose from {RETRIEVERS}")
        strategies = {"vector": self.vector, "graph": self.graph, "hybrid": self.hybrid}
        return strategies[retriever](question, k)

    # -- subgraph for the UI -------------------------------------------------------------
    def subgraph(self, result: RetrievalResult) -> dict:
        retrieved_docs = set(result.doc_ids())
        ids = unique(result.doc_ids() + [n for p in result.paths for n in p.node_ids])
        nodes, edges = [], []
        seen_edges: set[tuple] = set()
        for r in self.db.run(*q_nodes_edges(ids)):
            nodes.append(
                {
                    "id": r["id"],
                    "name": r["name"],
                    "type": r["type"],
                    "title": r.get("title"),
                    "retrieved": r["id"] in retrieved_docs,
                }
            )
            for e in r["out"]:
                key = (e["source"], e["type"], e["target"])
                if key not in seen_edges:
                    seen_edges.add(key)
                    edges.append(e)
        return {"nodes": nodes, "edges": edges}
