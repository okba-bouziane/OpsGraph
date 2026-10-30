from opsgraph.graph import q_entity, q_link_entities


def test_graph_counts(db):
    c = db.counts()
    assert c["chunks"] >= 100 and c["entities"] >= 90 and c["relationships"] > 400


def test_entities_are_not_mislabelled_as_chunks(db):
    assert db.run("MATCH (n:__Entity__:Chunk) RETURN count(n) AS n")[0]["n"] == 0


def test_vector_retrieval_finds_the_fact(retriever):
    res = retriever.vector("How long does a full rebuild of the search index take?", 3)
    assert res.chunks[0].doc_id == "RB-SEARCH-REINDEX"


def test_entity_linking_by_alias_alert_and_person(db):
    ids = {
        r["id"]
        for r in db.run(*q_link_entities("PaymentDeclineRateHigh fired on payments gateway, is Nabil Ferhat on call?"))
    }
    assert {"PaymentDeclineRateHigh", "SVC-PAYMENTS", "Nabil Ferhat"} <= ids


def test_graph_follows_owner_to_on_call_rota(retriever):
    res = retriever.graph("main-db is running out of connections: who do I page first?", 5)
    assert {"SVC-MAINDB", "ONC-PLATFORM"} <= set(res.doc_ids())
    # service -> owner team <- rota covering that team
    assert any("OWNED_BY" in p.describe() and "COVERS" in p.describe() for p in res.paths)


def test_blast_radius_follows_dependencies_backwards(retriever):
    res = retriever.graph("What breaks if main-db goes down?", 5)
    assert {"SVC-ORDERS", "SVC-CATALOG"} <= set(res.doc_ids())


def test_incident_to_decision(retriever):
    res = retriever.graph("What was decided after the card payment outage of August 2025?", 5)
    assert {"PM-2025-08", "ADR-003"} <= set(res.doc_ids())


def test_hybrid_fuses_both(retriever):
    res = retriever.hybrid("Who leads the team that owns search-api?", 5)
    assert {"SVC-SEARCH", "TEAM-DISCOVERY"} <= set(res.doc_ids())


def test_subgraph_contains_retrieved_docs(retriever):
    res = retriever.graph("Who is the primary on-call engineer for checkout-api?", 5)
    sg = retriever.subgraph(res)
    ids = {n["id"] for n in sg["nodes"]}
    assert {"SVC-CHECKOUT", "ONC-PAY"} <= ids and any(e["type"] == "OWNED_BY" for e in sg["edges"])


def test_entity_lookup(db):
    e = db.run(*q_entity("redis-cache"))[0]
    assert e["id"] == "SVC-REDIS" and e["type"] == "Service"
