"""Extraction schema: the entity and relation types the graph is allowed to contain.

The same Pydantic models are the structured-output contract for the LLM extractor and the
return type of the rule-based extractor, so both feed the graph builder identically.
"""

from typing import Literal

from pydantic import BaseModel, Field

EntityType = Literal[
    "Service",
    "Team",
    "Rota",
    "Runbook",
    "Postmortem",
    "Decision",
    "Person",
    "Alert",
    "ActionItem",
    "Date",
]

RelationType = Literal[
    "DEPENDS_ON",  # Service -> Service, property: how
    "OWNED_BY",  # Service -> Team
    "MEMBER_OF",  # Person -> Team, property: role
    "COVERS",  # Rota -> Team
    "ON_CALL",  # Person -> Rota, property: role (primary/secondary/escalation)
    "RUNBOOK_FOR",  # Runbook -> Service
    "FIRES_ON",  # Alert -> Service
    "HANDLED_BY",  # Alert -> Runbook
    "ROOT_CAUSE",  # Postmortem -> Service
    "IMPACTED",  # Postmortem -> Service
    "FOLLOW_UP",  # Postmortem -> Decision or Runbook
    "APPLIES_TO",  # Decision -> Service
    "SUPERSEDES",  # document -> document
    "REFERENCES",  # document -> document
    "HAS_ACTION",  # Postmortem -> ActionItem
    "ASSIGNED_TO",  # ActionItem -> Team
    "DATED",  # document -> Date, property: kind (incident/decided/updated)
]

DOCUMENT_TYPES = ("Service", "Team", "Rota", "Runbook", "Postmortem", "Decision")

# Entities a question can name directly (besides documents): people and alert names.
LINKABLE_TYPES = ("Person", "Alert", *DOCUMENT_TYPES)

# Relations followed during graph expansion. Dates and action items are leaf facts, so
# traversing them would connect unrelated documents.
TRAVERSAL_RELATIONS = (
    "DEPENDS_ON",
    "OWNED_BY",
    "MEMBER_OF",
    "COVERS",
    "ON_CALL",
    "RUNBOOK_FOR",
    "FIRES_ON",
    "HANDLED_BY",
    "ROOT_CAUSE",
    "IMPACTED",
    "FOLLOW_UP",
    "APPLIES_TO",
    "SUPERSEDES",
    "REFERENCES",
)


# What kind of document answers a question, from its wording: "who do I page" wants an on-call
# rota, "what was decided" a decision. The graph retriever boosts reached documents of that type.
INTENTS: tuple[tuple[str, str], ...] = (
    (r"\b(page|paged|on[- ]call|primary|secondary|escalation|who (do|should) i (call|page))\b", "Rota"),
    (r"\b(runbook|steps?|what (do|should) i do)\b", "Runbook"),
    (r"\b(decided|decisions?|adr-\d+)\b", "Decision"),
    (r"\b(incident|outage|postmortem|caused|root cause)\b", "Postmortem"),
    (r"\b(leads?|members?|which team|team owns)\b", "Team"),
    (r"\b(depends?|dependen\w*|breaks?|goes down|affected)\b", "Service"),
)


class ExtractedEntity(BaseModel):
    name: str = Field(description="Canonical name, e.g. 'SVC-CHECKOUT', 'Nabil Ferhat' or 'RedisDown'")
    type: EntityType
    properties: dict[str, str] = Field(default_factory=dict)


class ExtractedRelation(BaseModel):
    source: str = Field(description="Name of the source entity (must appear in entities)")
    relation: RelationType
    target: str = Field(description="Name of the target entity (must appear in entities)")
    properties: dict[str, str] = Field(default_factory=dict)


class Extraction(BaseModel):
    entities: list[ExtractedEntity] = Field(default_factory=list)
    relations: list[ExtractedRelation] = Field(default_factory=list)

    def validated(self) -> "Extraction":
        """Drop relations whose endpoints are not extracted entities; dedupe both lists."""
        seen: dict[tuple[str, str], ExtractedEntity] = {}
        for e in self.entities:
            seen.setdefault((e.type, e.name.strip()), e)
        names = {n for _, n in seen}
        rels: dict[tuple[str, str, str], ExtractedRelation] = {}
        for r in self.relations:
            if r.source.strip() in names and r.target.strip() in names:
                rels.setdefault((r.source.strip(), r.relation, r.target.strip()), r)
        return Extraction(entities=list(seen.values()), relations=list(rels.values()))


def entity_id(name: str) -> str:
    """Stable node id. Names are unique across types in this corpus (document IDs, people,
    alert names, ISO dates), so the trimmed name is the id."""
    return name.strip()
