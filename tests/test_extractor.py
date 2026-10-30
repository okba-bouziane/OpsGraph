import pytest
from pydantic import ValidationError

from opsgraph.corpus import load_corpus
from opsgraph.extract import LLMExtractor, RuleExtractor, build_registry
from opsgraph.schema import ExtractedEntity, ExtractedRelation, Extraction

DOCS = {d.doc_id: d for d in load_corpus()}
REG = build_registry(list(DOCS.values()))


def rels(ex, relation):
    return {(r.source, r.target) for r in ex.relations if r.relation == relation}


def test_corpus_size_and_labels():
    assert len(DOCS) == 36
    assert all("Sample data, fictional" in d.text for d in DOCS.values())
    assert sorted(set(REG.values())) == ["Decision", "Postmortem", "Rota", "Runbook", "Service", "Team"]


def test_service_dependencies_owner_and_alerts():
    ex = RuleExtractor().extract(DOCS["SVC-CHECKOUT"], REG)
    assert ("SVC-CHECKOUT", "SVC-REDIS") in rels(ex, "DEPENDS_ON")
    assert ("SVC-CHECKOUT", "TEAM-PAY") in rels(ex, "OWNED_BY")
    assert ("CheckoutHighErrorRate", "SVC-CHECKOUT") in rels(ex, "FIRES_ON")
    how = {r.target: r.properties["how"] for r in ex.relations if r.relation == "DEPENDS_ON"}
    assert how["SVC-REDIS"] == "cart storage"
    entity = next(e for e in ex.entities if e.name == "SVC-CHECKOUT")
    assert entity.properties["alias"] == "checkout-api" and entity.properties["tier"] == "1"


def test_team_members_and_rota_roles():
    team = RuleExtractor().extract(DOCS["TEAM-PAY"], REG)
    roles = {r.source: r.properties["role"] for r in team.relations if r.relation == "MEMBER_OF"}
    assert roles["Yasmine Ait Ali"] == "Lead"
    rota = RuleExtractor().extract(DOCS["ONC-PAY"], REG)
    on_call = {r.properties["role"]: r.source for r in rota.relations if r.relation == "ON_CALL"}
    assert on_call == {"primary": "Nabil Ferhat", "secondary": "Lina Cherif", "escalation": "Yasmine Ait Ali"}
    assert ("ONC-PAY", "TEAM-PAY") in rels(rota, "COVERS")


def test_runbook_handles_alerts_and_supersedes():
    ex = RuleExtractor().extract(DOCS["RB-REDIS-FAILOVER"], REG)
    assert ("RedisDown", "RB-REDIS-FAILOVER") in rels(ex, "HANDLED_BY")
    assert ("RB-REDIS-FAILOVER", "SVC-REDIS") in rels(ex, "RUNBOOK_FOR")
    assert ("RB-REDIS-FAILOVER", "RB-REDIS-RESTART") in rels(ex, "SUPERSEDES")
    types = {e.name: e.type for e in ex.entities}
    assert types["RB-REDIS-RESTART"] == "Runbook" and types["SVC-REDIS"] == "Service"


def test_postmortem_links_and_action_items():
    ex = RuleExtractor().extract(DOCS["PM-2025-03"], REG)
    assert ("PM-2025-03", "SVC-REDIS") in rels(ex, "ROOT_CAUSE")
    assert {("PM-2025-03", "SVC-CHECKOUT"), ("PM-2025-03", "SVC-STOREFRONT")} <= rels(ex, "IMPACTED")
    assert {("PM-2025-03", "ADR-002"), ("PM-2025-03", "RB-REDIS-FAILOVER")} <= rels(ex, "FOLLOW_UP")
    actions = [e for e in ex.entities if e.type == "ActionItem"]
    assert len(actions) == 3
    platform = next(a for a in actions if "TEAM-PLATFORM" in a.name)
    assert platform.properties["due"] == "2025-04-30"
    assert (platform.name, "TEAM-PLATFORM") in rels(ex, "ASSIGNED_TO")


def test_decision_applies_and_supersedes():
    ex = RuleExtractor().extract(DOCS["ADR-002"], REG)
    assert ("ADR-002", "ADR-001") in rels(ex, "SUPERSEDES")
    assert ("ADR-002", "SVC-REDIS") in rels(ex, "APPLIES_TO")
    assert ("ADR-002", "PM-2025-03") in rels(ex, "REFERENCES")


def test_every_doc_extracts_with_valid_endpoints():
    for d in DOCS.values():
        ex = RuleExtractor().extract(d, REG)
        names = {e.name for e in ex.entities}
        assert all(r.source in names and r.target in names for r in ex.relations)
        assert any(e.name == d.doc_id for e in ex.entities)


def test_schema_rejects_unknown_types_and_validated_drops_dangling():
    with pytest.raises(ValidationError):
        ExtractedEntity(name="x", type="Planet")  # type: ignore[arg-type]
    ex = Extraction(
        entities=[ExtractedEntity(name="A", type="Service"), ExtractedEntity(name="A", type="Service")],
        relations=[ExtractedRelation(source="A", relation="DEPENDS_ON", target="Missing")],
    ).validated()
    assert len(ex.entities) == 1 and ex.relations == []


class ScriptedClient:
    """Test double standing in for the LLM client; returns a canned structured result."""

    def structured(self, schema, system, user):
        return schema(
            entities=[
                ExtractedEntity(name="SVC-CHECKOUT", type="Service"),
                ExtractedEntity(name="TEAM-PAY", type="Team"),
            ],
            relations=[
                ExtractedRelation(source="SVC-CHECKOUT", relation="OWNED_BY", target="TEAM-PAY"),
                ExtractedRelation(source="SVC-CHECKOUT", relation="DEPENDS_ON", target="Nope"),
            ],
        )


def test_llm_extractor_uses_structured_output_and_validates():
    ex = LLMExtractor(client=ScriptedClient()).extract(DOCS["SVC-CHECKOUT"], REG)
    assert len(ex.relations) == 1
