"""Build the graph: chunks with embeddings, extracted entities and relations, provenance links.

Graph shape:
  (:Chunk)-[:FROM_DOC]->(document)      every chunk points at its document entity
  (:Chunk)-[:MENTIONS]->(entity)        chunk text contains the entity (or its action-item text)
  (entity)-[typed relations]->(entity)  from the extractor, schema in opsgraph.schema
"""

import re
import sys
from dataclasses import asdict, dataclass

from llama_index.core.graph_stores.types import ChunkNode, EntityNode, Relation

from opsgraph.corpus import Doc, chunk_doc, load_corpus
from opsgraph.embeddings import get_embedder
from opsgraph.extract import Extractor, build_registry, get_extractor
from opsgraph.graph import GraphDB, match_names
from opsgraph.schema import DOCUMENT_TYPES, LINKABLE_TYPES, ExtractedEntity, Extraction, entity_id


@dataclass
class IngestStats:
    extractor: str
    documents: int
    chunks: int
    entities: int
    relations: int
    mentions: int

    def as_dict(self) -> dict:
        return asdict(self)


PROBE_CHARS = 80  # a chunk "mentions" an entity if the first 80 characters of its text/name occur in the chunk


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _entity_nodes(extraction: Extraction, registry: dict[str, str]) -> list[EntityNode]:
    """One LlamaIndex node per distinct entity; repeated mentions merge their properties."""
    nodes: dict[str, EntityNode] = {}
    for e in extraction.entities:
        eid = entity_id(e.name)
        label = registry.get(eid, e.type) if e.type in DOCUMENT_TYPES else e.type
        props = {k: v for k, v in e.properties.items() if k != "text"} | {"id": eid}
        if eid in nodes:
            props = {**nodes[eid].properties, **props}
        if label in LINKABLE_TYPES:
            props["match_names"] = match_names(e.name, props.get("alias", ""))
        nodes[eid] = EntityNode(name=eid, label=label, properties=props)
    return list(nodes.values())


def _relations(extraction: Extraction) -> list[Relation]:
    return [
        Relation(
            label=r.relation,
            source_id=entity_id(r.source),
            target_id=entity_id(r.target),
            properties=r.properties,
        )
        for r in extraction.relations
    ]


def _mention_probe(entity: ExtractedEntity) -> str:
    """Text to look for in chunks: the action item's wording, else the entity name."""
    text = _norm(entity.properties.get("text", ""))
    return text if entity.type == "ActionItem" else text or _norm(entity.name)


def _provenance(doc: Doc, extraction: Extraction, chunks: list) -> list[Relation]:
    """FROM_DOC links for every chunk and MENTIONS links from chunks to the entities they contain."""
    doc_entity = entity_id(doc.doc_id)
    links = [Relation(label="FROM_DOC", source_id=c.id_, target_id=doc_entity) for c in chunks]
    chunk_texts = {c.id_: _norm(c.text) for c in chunks}
    seen: set[tuple[str, str]] = set()
    for e in extraction.entities:
        eid = entity_id(e.name)
        probe = _mention_probe(e)[:PROBE_CHARS]
        if eid == doc_entity or not probe:
            continue
        for chunk_id, text in chunk_texts.items():
            if probe in text and (chunk_id, eid) not in seen:
                seen.add((chunk_id, eid))
                links.append(Relation(label="MENTIONS", source_id=chunk_id, target_id=eid))
    return links


def build_graph_records(
    doc: Doc, extraction: Extraction, registry: dict[str, str], chunks: list
) -> tuple[list[EntityNode], list[Relation], list[Relation]]:
    """Convert one document's extraction into (entities, relations, provenance links). No I/O."""
    return _entity_nodes(extraction, registry), _relations(extraction), _provenance(doc, extraction, chunks)


def _merge_entities(entities: dict[str, EntityNode], new: list[EntityNode]) -> None:
    """Add entities to the corpus-wide map; an entity seen in several documents keeps all its properties."""
    for node in new:
        if node.name in entities:
            props = {**entities[node.name].properties, **node.properties}
            if "alias" in props:
                props["match_names"] = match_names(node.name, props["alias"])
            node = EntityNode(name=node.name, label=node.label, properties=props)
        entities[node.name] = node


def _chunk_nodes(chunks: list, vectors: list[list[float]]) -> list[ChunkNode]:
    return [
        ChunkNode(
            text=c.text,
            id_=c.id_,
            label="Chunk",
            embedding=vector,
            properties={"doc_id": c.metadata["doc_id"], "title": c.metadata["title"]},
        )
        for c, vector in zip(chunks, vectors, strict=True)
    ]


def ingest(
    extractor: Extractor | str = "rules",
    reset: bool = True,
    db: GraphDB | None = None,
    docs: list[Doc] | None = None,
) -> IngestStats:
    """Chunk and embed the corpus, extract entities and relations, and write everything to Neo4j."""
    if isinstance(extractor, str):
        extractor = get_extractor(extractor)
    docs = docs or load_corpus()
    registry = build_registry(docs)
    own_db = db is None
    db = db or GraphDB()
    try:
        db.ensure_schema()
        if reset:
            db.reset()
        chunks_by_doc = {d.doc_id: chunk_doc(d) for d in docs}
        all_chunks = [c for chunks in chunks_by_doc.values() for c in chunks]
        vectors = get_embedder().get_text_embedding_batch([c.text for c in all_chunks], show_progress=False)
        db.store.upsert_nodes(_chunk_nodes(all_chunks, vectors))

        entities: dict[str, EntityNode] = {}
        relations: list[Relation] = []
        provenance: list[Relation] = []
        for doc in docs:
            extraction = extractor.extract(doc, registry)
            doc_entities, doc_relations, doc_links = build_graph_records(
                doc, extraction, registry, chunks_by_doc[doc.doc_id]
            )
            _merge_entities(entities, doc_entities)
            relations += doc_relations
            provenance += doc_links
        # Entities first: upserting a relation to a missing node would create it as a Chunk.
        db.store.upsert_nodes(list(entities.values()))
        db.store.upsert_relations(relations)
        db.store.upsert_relations(provenance)
        return IngestStats(extractor.name, len(docs), len(all_chunks), len(entities), len(relations), len(provenance))
    finally:
        if own_db:
            db.close()


if __name__ == "__main__":
    kind = sys.argv[1] if len(sys.argv) > 1 else "rules"
    print(ingest(kind).as_dict())
