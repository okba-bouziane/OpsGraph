"""Neo4j access: LlamaIndex property graph store plus Cypher builders for retrieval.

The Cypher builders are pure functions returning (query, params) so they can be unit
tested without a database and read in one place.
"""

from typing import Any

from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore

from opsgraph import config
from opsgraph.schema import DOCUMENT_TYPES, LINKABLE_TYPES, TRAVERSAL_RELATIONS

CHUNK_INDEX = "chunk_embedding"
DOC_LABELS = " OR ".join(f"d:{t}" for t in DOCUMENT_TYPES)
LINK_LABELS = " OR ".join(f"d:{t}" for t in LINKABLE_TYPES)
HOP_RELS = "|".join(TRAVERSAL_RELATIONS)


def _type_of(var: str) -> str:
    """Cypher expression for a node's entity type, skipping LlamaIndex's internal `__...__` labels."""
    return f"[l IN labels({var}) WHERE NOT l STARTS WITH '__'][0]"


def match_names(name: str, extra: str = "") -> list[str]:
    """Strings that identify an entity in a user question: its id, its alias ("checkout-api"),
    and the alias with spaces instead of dashes ("checkout api")."""
    out = [name]
    for candidate in (extra, extra.replace("-", " ")):
        if candidate and candidate not in out:
            out.append(candidate)
    return out


# ---- Cypher builders ---------------------------------------------------------------


def q_chunk_vector_search(k: int, embedding: list[float]) -> tuple[str, dict[str, Any]]:
    """ANN search on the Neo4j vector index, oversampled then re-scored with exact cosine.

    The HNSW index is approximate; on a graph that was reset and rebuilt it can miss true
    nearest neighbours, so candidates are over-fetched and ranked exactly before the top k.
    """
    return (
        f"""CALL db.index.vector.queryNodes('{CHUNK_INDEX}', $fetch, $embedding)
        YIELD node
        WITH node, vector.similarity.cosine(node.embedding, $embedding) AS score
        RETURN node.id AS chunk_id, node.text AS text, node.doc_id AS doc_id, score
        ORDER BY score DESC LIMIT $k""",
        {"k": k, "fetch": max(k * config.VECTOR_OVERSAMPLE, config.VECTOR_MIN_FETCH), "embedding": embedding},
    )


def q_link_entities(question: str) -> tuple[str, dict[str, Any]]:
    """Entities (documents, people, alerts) whose id or alias occurs in the question."""
    return (
        f"""MATCH (d:__Entity__)
        WHERE ({LINK_LABELS})
          AND any(m IN d.match_names WHERE toLower($q) CONTAINS toLower(m))
        RETURN d.id AS id, d.name AS name, labels(d) AS labels""",
        {"q": question},
    )


def q_expand(max_hops: int, seed_ids: list[str]) -> tuple[str, dict[str, Any]]:
    """Documents reachable from seed entities within `max_hops`, with the shortest path to each."""
    hops = int(max_hops)
    return (
        f"""MATCH (s:__Entity__) WHERE s.id IN $seed_ids
        MATCH p = (s)-[:{HOP_RELS}*1..{hops}]-(d:__Entity__)
        WHERE ({DOC_LABELS}) AND d.id <> s.id
          AND size(apoc.coll.toSet(nodes(p))) = size(nodes(p))
        WITH d, p ORDER BY length(p)
        WITH d, collect(p)[0] AS best
        RETURN d.id AS doc_id, length(best) AS hops,
               [n IN nodes(best) | n.id] AS node_ids,
               [r IN relationships(best) |
                  {{type: type(r), source: startNode(r).id, target: endNode(r).id}}] AS edges""",
        {"seed_ids": seed_ids},
    )


def q_chunks_of_docs(doc_ids: list[str], embedding: list[float]) -> tuple[str, dict[str, Any]]:
    return (
        f"""MATCH (c:Chunk)-[:FROM_DOC]->(d:__Entity__) WHERE c.doc_id IN $doc_ids
        RETURN c.id AS chunk_id, c.text AS text, c.doc_id AS doc_id, {_type_of("d")} AS doc_type,
               vector.similarity.cosine(c.embedding, $embedding) AS score""",
        {"doc_ids": doc_ids, "embedding": embedding},
    )


def q_shortest_path(a: str, b: str, max_hops: int) -> tuple[str, dict[str, Any]]:
    hops = int(max_hops) + 1
    return (
        f"""MATCH (a:__Entity__ {{id: $a}}), (b:__Entity__ {{id: $b}})
        MATCH p = shortestPath((a)-[:{HOP_RELS}*..{hops}]-(b))
        RETURN [n IN nodes(p) | n.id] AS node_ids,
               [r IN relationships(p) |
                  {{type: type(r), source: startNode(r).id, target: endNode(r).id}}] AS edges""",
        {"a": a, "b": b},
    )


def q_nodes_edges(node_ids: list[str]) -> tuple[str, dict[str, Any]]:
    """Nodes and the traversal relationships among them, for the UI graph view."""
    return (
        f"""MATCH (n:__Entity__) WHERE n.id IN $ids
        OPTIONAL MATCH (n)-[r:{HOP_RELS}]->(m:__Entity__) WHERE m.id IN $ids
        RETURN n.id AS id, n.name AS name,
               {_type_of("n")} AS type,
               n.title AS title,
               collect(CASE WHEN r IS NULL THEN NULL
                   ELSE {{type: type(r), source: n.id, target: m.id, role: r.role}} END) AS out""",
        {"ids": node_ids},
    )


def q_entity(name: str) -> tuple[str, dict[str, Any]]:
    return (
        f"""MATCH (e:__Entity__)
        WHERE toLower(e.id) = toLower($name)
           OR any(m IN e.match_names WHERE toLower(m) = toLower($name))
        RETURN e.id AS id, e.name AS name,
               {_type_of("e")} AS type,
               e{{.*, embedding: null, match_names: null}} AS properties
        LIMIT 1""",
        {"name": name},
    )


def q_entity_neighbours(entity_id: str) -> tuple[str, dict[str, Any]]:
    return (
        f"""MATCH (e:__Entity__ {{id: $id}})-[r]-(n:__Entity__)
        RETURN type(r) AS relation, startNode(r).id = e.id AS outgoing, r.role AS role,
               n.id AS id, n.name AS name,
               {_type_of("n")} AS type
        ORDER BY relation, name""",
        {"id": entity_id},
    )


def q_is_document(entity_id: str) -> tuple[str, dict[str, Any]]:
    return (
        f"MATCH (d:__Entity__ {{id: $id}}) RETURN {DOC_LABELS} AS is_doc",
        {"id": entity_id},
    )


def q_counts() -> str:
    return (
        "RETURN COUNT { (n:__Node__) } AS nodes, COUNT { (c:Chunk) } AS chunks, "
        "COUNT { (e:__Entity__) } AS entities, COUNT { ()-[]->() } AS relationships"
    )


# ---- Store wrapper -----------------------------------------------------------------


class GraphDB:
    """Thin wrapper over the LlamaIndex Neo4j store: connection, schema setup and raw Cypher."""

    def __init__(self) -> None:
        self.store = Neo4jPropertyGraphStore(
            username=config.NEO4J_USER,
            password=config.NEO4J_PASSWORD,
            url=config.NEO4J_URI,
            database=config.NEO4J_DATABASE,
            refresh_schema=False,
            create_indexes=False,
        )

    def run(self, query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return self.store.structured_query(query, param_map=params or {}) or []

    def ensure_schema(self) -> None:
        self.run("CREATE CONSTRAINT lex_node_id IF NOT EXISTS FOR (n:__Node__) REQUIRE n.id IS UNIQUE")
        self.run(
            f"""CREATE VECTOR INDEX {CHUNK_INDEX} IF NOT EXISTS FOR (c:Chunk) ON (c.embedding)
            OPTIONS {{indexConfig: {{`vector.dimensions`: {config.EMBEDDING_DIM},
                                     `vector.similarity_function`: 'cosine'}}}}"""
        )

    def reset(self) -> None:
        self.run("MATCH (n:__Node__) DETACH DELETE n")

    def counts(self) -> dict[str, int]:
        rows = self.run(q_counts())
        return {k: int(v) for k, v in rows[0].items()} if rows else {}

    def ping(self) -> bool:
        try:
            self.run("RETURN 1 AS ok")
            return True
        except Exception:
            return False

    def close(self) -> None:
        self.store.close()
