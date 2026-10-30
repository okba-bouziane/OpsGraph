from typing import Protocol

from opsgraph.corpus import Doc
from opsgraph.schema import DOCUMENT_TYPES, Extraction


def doc_type(doc: Doc) -> str:
    """The header "Type" value is the graph label; anything unknown is treated as a Service page."""
    t = doc.meta.get("Type", "Service")
    return t if t in DOCUMENT_TYPES else "Service"


def build_registry(docs: list[Doc]) -> dict[str, str]:
    """doc id -> document type, so a reference to another document resolves to the right label."""
    return {d.doc_id: doc_type(d) for d in docs}


class Extractor(Protocol):
    name: str

    def extract(self, doc: Doc, registry: dict[str, str]) -> Extraction: ...
