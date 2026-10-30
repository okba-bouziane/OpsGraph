"""LLM extractor: structured outputs (Pydantic schema) through an OpenAI-compatible endpoint."""

from opsgraph.corpus import Doc
from opsgraph.llm import LLMClient
from opsgraph.schema import DOCUMENT_TYPES, Extraction

SYSTEM = f"""You extract a knowledge graph from one engineering document (service page, team page,
on-call rota, runbook, incident postmortem or architecture decision).
Entity types: {", ".join(DOCUMENT_TYPES)}, Person, Alert, ActionItem, Date.
Use the document ID (e.g. SVC-CHECKOUT) as the entity name for the document itself and for any other
document it refers to. Name people and alerts exactly as written. Dates are ISO (YYYY-MM-DD).
Relations (source -> target): DEPENDS_ON (Service -> Service, properties.how), OWNED_BY (Service ->
Team), MEMBER_OF (Person -> Team, properties.role), COVERS (Rota -> Team), ON_CALL (Person -> Rota,
properties.role = primary|secondary|escalation), RUNBOOK_FOR (Runbook -> Service), FIRES_ON (Alert ->
Service), HANDLED_BY (Alert -> Runbook), ROOT_CAUSE and IMPACTED (Postmortem -> Service), FOLLOW_UP
(Postmortem -> Decision or Runbook), APPLIES_TO (Decision -> Service), SUPERSEDES, REFERENCES,
HAS_ACTION (Postmortem -> ActionItem, properties.due), ASSIGNED_TO (ActionItem -> Team), DATED
(document -> Date, properties.kind). Only extract facts stated in the text. Every relation endpoint
must also be listed in entities."""


class LLMExtractor:
    name = "llm"

    def __init__(self, client: LLMClient | None = None):
        self.client = client or LLMClient()

    def extract(self, doc: Doc, registry: dict[str, str]) -> Extraction:
        known = ", ".join(f"{k} ({v})" for k, v in sorted(registry.items()))
        user = f"Known document IDs and types: {known}\n\nDocument:\n{doc.text}"
        return self.client.structured(Extraction, SYSTEM, user).validated()
