"""Load the sample corpus and split it into chunks (one header chunk + one chunk per section)."""

import re
from dataclasses import dataclass, field
from pathlib import Path

from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode

from opsgraph import config

META_RE = re.compile(r"^([A-Za-z -]+):\s*(.+)$")


@dataclass
class Doc:
    doc_id: str
    title: str
    text: str
    meta: dict[str, str] = field(default_factory=dict)


def parse_doc(text: str) -> Doc:
    lines = text.splitlines()
    title = lines[0].lstrip("# ").strip() if lines else ""
    meta: dict[str, str] = {}
    for line in lines[1:]:
        if line.startswith("##"):
            break
        m = META_RE.match(line.strip())
        if m:
            meta[m.group(1).strip()] = m.group(2).strip()
    return Doc(doc_id=meta.get("Document ID", ""), title=title, text=text, meta=meta)


def load_corpus(directory: Path | None = None) -> list[Doc]:
    directory = Path(directory or config.DATA_DIR)
    docs = [parse_doc(p.read_text()) for p in sorted(directory.glob("*.md"))]
    return [d for d in docs if d.doc_id]


def chunk_doc(doc: Doc) -> list[TextNode]:
    """Header chunk (title + metadata) and one chunk per `###` section or `##` block."""
    parts = re.split(r"\n(?=##+ )", doc.text)
    prefix = f"[{doc.doc_id}] {doc.title}\n"
    nodes: list[TextNode] = []
    splitter = SentenceSplitter(chunk_size=256, chunk_overlap=20)
    for i, part in enumerate(parts):
        body = part.strip()
        if not body:
            continue
        pieces = [body] if len(body) < 1200 else splitter.split_text(body)
        for j, piece in enumerate(pieces):
            text = piece if i == 0 else prefix + piece
            nodes.append(
                TextNode(
                    id_=f"{doc.doc_id}#{i}.{j}",
                    text=text,
                    metadata={"doc_id": doc.doc_id, "title": doc.title, "section": i},
                )
            )
    return nodes
