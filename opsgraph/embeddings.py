"""Local embeddings (fastembed, ONNX; no API key). Model is downloaded on first use."""

from functools import lru_cache

from llama_index.embeddings.fastembed import FastEmbedEmbedding

from opsgraph import config


@lru_cache(maxsize=1)
def get_embedder() -> FastEmbedEmbedding:
    return FastEmbedEmbedding(model_name=config.EMBEDDING_MODEL)
