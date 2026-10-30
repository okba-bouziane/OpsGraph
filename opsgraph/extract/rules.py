"""Deterministic rule-based extractor.

It reads the metadata block and the action-item lines of the sample corpus and needs no network
or key. It is tuned to this corpus format: a reproducible baseline and test fixture, not a
general parser (the LLM extractor handles free-form text).
"""

import re

from opsgraph.corpus import Doc
from opsgraph.extract.base import doc_type
from opsgraph.schema import ExtractedEntity, ExtractedRelation, Extraction

# "SVC-PAYMENTS (critical)" or "Yasmine Ait Ali (Lead)": a name with an optional note in brackets.
NOTE_RE = re.compile(r"^(.*?)\s*\(([^()]+)\)\s*$")
ACTION_RE = re.compile(r"^- (?P<team>TEAM-[A-Z]+) will (?P<what>.+?) by (?P<due>\d{4}-\d{2}-\d{2})\.\s*$", re.M)
TITLE_RE = re.compile(r"^(Service|Team|On-call rota|Runbook|Postmortem|Decision):\s*")


def _split_list(value: str) -> list[str]:
    return [p.strip() for p in re.split(r"[;,]", value) if p.strip()]


def _with_note(item: str) -> tuple[str, str]:
    m = NOTE_RE.match(item)
    return (m.group(1).strip(), m.group(2).strip()) if m else (item.strip(), "")


def _alias(title: str) -> str:
    """'Service: checkout-api' -> 'checkout-api', the name people use in questions."""
    return TITLE_RE.sub("", title).strip()


class RuleExtractor:
    name = "rules"

    def extract(self, doc: Doc, registry: dict[str, str]) -> Extraction:
        ents: list[ExtractedEntity] = []
        rels: list[ExtractedRelation] = []
        meta = doc.meta
        did = doc.doc_id
        dtype = doc_type(doc)
        props = {"title": doc.title, "alias": _alias(doc.title)}
        for key in ("Kind", "Tier", "Severity", "Status", "Duration"):
            if key in meta:
                props[key.lower()] = meta[key]
        ents.append(ExtractedEntity(name=did, type=dtype, properties=props))  # type: ignore[arg-type]

        def link(target: str, relation: str, source: str = did, **properties: str) -> None:
            ents.append(ExtractedEntity(name=target, type=registry.get(target, "Service")))  # type: ignore[arg-type]
            rels.append(ExtractedRelation(source=source, relation=relation, target=target, properties=properties))  # type: ignore[arg-type]

        for item in _split_list(meta.get("Depends on", "")):
            target, how = _with_note(item)
            link(target, "DEPENDS_ON", how=how)
        for key, relation in (
            ("Owner", "OWNED_BY"),
            ("Covers", "COVERS"),
            ("Service", "RUNBOOK_FOR"),
            ("Root cause", "ROOT_CAUSE"),
            ("Impacted", "IMPACTED"),
            ("Follow-ups", "FOLLOW_UP"),
            ("Applies to", "APPLIES_TO"),
            ("Supersedes", "SUPERSEDES"),
            ("References", "REFERENCES"),
        ):
            for target in _split_list(meta.get(key, "")):
                link(target, relation)

        for item in _split_list(meta.get("Members", "")):
            person, role = _with_note(item)
            ents.append(ExtractedEntity(name=person, type="Person"))
            rels.append(ExtractedRelation(source=person, relation="MEMBER_OF", target=did, properties={"role": role}))
        for key in ("Primary", "Secondary", "Escalation"):
            if key in meta:
                ents.append(ExtractedEntity(name=meta[key], type="Person"))
                rels.append(
                    ExtractedRelation(
                        source=meta[key], relation="ON_CALL", target=did, properties={"role": key.lower()}
                    )
                )

        # An alert listed on a service page fires on that service; on a runbook, the runbook handles it.
        alert_rel = "HANDLED_BY" if dtype == "Runbook" else "FIRES_ON"
        for alert in _split_list(meta.get("Alerts", "")):
            ents.append(ExtractedEntity(name=alert, type="Alert"))
            rels.append(ExtractedRelation(source=alert, relation=alert_rel, target=did))  # type: ignore[arg-type]

        for key, kind in (("Date", "incident" if dtype == "Postmortem" else "decided"), ("Updated", "updated")):
            if key in meta:
                ents.append(ExtractedEntity(name=meta[key], type="Date"))
                rels.append(
                    ExtractedRelation(source=did, relation="DATED", target=meta[key], properties={"kind": kind})
                )

        for m in ACTION_RE.finditer(doc.text):
            team, what, due = m.group("team"), m.group("what").strip(), m.group("due")
            name = f"{did} action: {team} will {what[:48]}"
            ents.append(
                ExtractedEntity(name=name, type="ActionItem", properties={"text": m.group(0)[2:].strip(), "due": due})
            )
            ents.append(ExtractedEntity(name=team, type="Team"))
            rels.append(ExtractedRelation(source=did, relation="HAS_ACTION", target=name))
            rels.append(ExtractedRelation(source=name, relation="ASSIGNED_TO", target=team))

        return Extraction(entities=ents, relations=rels).validated()
