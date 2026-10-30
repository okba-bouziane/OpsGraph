import pytest
from fastapi.testclient import TestClient

from opsgraph.api import app


@pytest.fixture(scope="module")
def client(db):
    with TestClient(app) as c:
        yield c


def test_health(client):
    h = client.get("/health").json()
    assert h["status"] == "ok" and h["neo4j"] is True and h["graph"]["chunks"] > 0


def test_ask_returns_answer_citations_path_and_subgraph(client):
    r = client.post(
        "/ask", json={"question": "Who is the primary on-call engineer for checkout-api?", "retriever": "graph"}
    )
    assert r.status_code == 200
    d = r.json()
    assert d["answer"] and d["citations"] and d["retriever"] == "graph"
    assert any(c["doc_id"] == "ONC-PAY" for c in d["citations"])
    assert d["subgraph"]["nodes"] and d["paths"]


def test_ask_validation(client):
    assert client.post("/ask", json={"question": "x"}).status_code == 422
    assert client.post("/ask", json={"question": "valid question here", "retriever": "bogus"}).status_code == 422


def test_entity_endpoint(client):
    d = client.get("/graph/entity/checkout-api").json()
    assert d["id"] == "SVC-CHECKOUT" and d["type"] == "Service"
    assert any(n["relation"] == "OWNED_BY" and n["id"] == "TEAM-PAY" for n in d["neighbours"])
    assert any(n["relation"] == "DEPENDS_ON" and n["id"] == "SVC-REDIS" for n in d["neighbours"])
    assert client.get("/graph/entity/Nobody Here").status_code == 404


def test_ingest_rebuilds_graph(client):
    r = client.post("/ingest", json={"extractor": "rules"})
    assert r.status_code == 200 and r.json()["documents"] == 36
    assert client.get("/health").json()["graph"]["entities"] > 80
