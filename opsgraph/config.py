"""Central configuration, read from environment variables (.env)."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", ROOT_DIR / "data" / "corpus"))
EVAL_DIR = ROOT_DIR / "evals"

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7688")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "opsgraph-pass")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
EMBEDDING_DIM = 384

# OpenAI-compatible endpoint. Defaults suit Groq; for Ollama use
# LLM_BASE_URL=http://localhost:11434/v1, LLM_API_KEY=ollama, LLM_MODEL=llama3.1.
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
LLM_REASONING_EFFORT = os.getenv("LLM_REASONING_EFFORT", "")  # optional: low | medium | high

# Retrieval
TOP_K = int(os.getenv("TOP_K", "5"))
SEED_K = 3  # vector seeds used to start graph expansion
MAX_HOPS = 3  # relationship hops in the neighbourhood expansion
HOP_DECAY = 0.9  # score multiplier per hop for chunks reached through the graph
RRF_K = 60  # reciprocal rank fusion constant used by the hybrid retriever
INTENT_BOOST = 1.2  # score multiplier for documents of the type the question asks for (see schema.INTENTS)
HEADER_BOOST = 1.1  # header chunk of a document reached through an edge: it holds the metadata the edge came from
MAX_PATHS_SHOWN = 6  # graph paths returned with an answer, shortest first
MAX_ENTITY_PAIRS = 10  # pairs of named entities connected with shortest-path queries
VECTOR_OVERSAMPLE = 4  # candidates fetched per requested chunk before exact re-scoring
VECTOR_MIN_FETCH = 30

MAX_ANSWER_ATTEMPTS = 2  # the query flow retries once, wider, when an answer is not grounded


def llm_configured() -> bool:
    return bool(LLM_API_KEY)
