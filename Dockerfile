FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 FASTEMBED_CACHE_PATH=/app/.fastembed_cache
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY opsgraph ./opsgraph
COPY data ./data
COPY evals ./evals
# Pre-download the embedding model so the container starts offline-ready
RUN python -c "from opsgraph.embeddings import get_embedder; get_embedder()"
EXPOSE 8001
CMD ["uvicorn", "opsgraph.api:app", "--host", "0.0.0.0", "--port", "8001"]
