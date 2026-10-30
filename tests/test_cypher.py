from opsgraph import config
from opsgraph.graph import (
    match_names,
    q_chunk_vector_search,
    q_expand,
    q_link_entities,
    q_shortest_path,
)
from opsgraph.retrieval import intent_types
from opsgraph.schema import TRAVERSAL_RELATIONS


def test_vector_query_oversamples_and_rescores():
    q, p = q_chunk_vector_search(5, [0.1] * config.EMBEDDING_DIM)
    assert "db.index.vector.queryNodes" in q and "similarity.cosine" in q
    assert p["k"] == 5 and p["fetch"] >= 30


def test_expand_uses_only_traversal_relations_and_hop_limit():
    q, p = q_expand(3, ["SVC-CHECKOUT"])
    for rel in TRAVERSAL_RELATIONS:
        assert rel in q
    assert "DATED" not in q and "HAS_ACTION" not in q  # leaf facts are not traversed
    assert "*1..3" in q and p == {"seed_ids": ["SVC-CHECKOUT"]}


def test_hop_count_is_an_int_not_injectable():
    q, _ = q_expand(int("2"), [])
    assert "*1..2" in q


def test_shortest_path_params():
    q, p = q_shortest_path("A", "B", 3)
    assert "shortestPath" in q and p == {"a": "A", "b": "B"}


def test_link_entities_is_parameterised():
    q, p = q_link_entities("x'); MATCH (n) DETACH DELETE n //")
    assert "DELETE" not in q and "$q" in q and p["q"].startswith("x'")


def test_match_names():
    assert match_names("SVC-CHECKOUT", "checkout-api") == ["SVC-CHECKOUT", "checkout-api", "checkout api"]
    assert match_names("Nabil Ferhat") == ["Nabil Ferhat"]


def test_intent_types():
    assert intent_types("Who do I page if checkout-api fails?") == {"Rota"}
    assert intent_types("What was decided after the outage?") == {"Decision", "Postmortem"}
    assert intent_types("What breaks if main-db goes down?") == {"Service"}
    assert intent_types("How much memory does Redis have?") == set()
