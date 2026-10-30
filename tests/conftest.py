import os

os.environ["LLM_API_KEY"] = ""  # tests never call a live model

import pytest

from opsgraph.graph import GraphDB
from opsgraph.ingest import ingest

NEO4J_DOWN = "Neo4j is not reachable (start it with `docker compose up -d neo4j`)"


@pytest.fixture(scope="session")
def db():
    try:
        database = GraphDB()
    except Exception:  # the store connects in its constructor
        pytest.skip(NEO4J_DOWN)
    if not database.ping():
        pytest.skip(NEO4J_DOWN)
    ingest("rules", reset=True, db=database)
    yield database
    database.close()


@pytest.fixture(scope="session")
def retriever(db):
    from opsgraph.retrieval import Retriever

    return Retriever(db)
