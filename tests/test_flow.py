from opsgraph.flow import ask, build_flow, heuristic_kind, lexical_grounded
from opsgraph.retrieval import RetrievalResult, RetrievedChunk


def test_heuristic_kind():
    assert heuristic_kind("Who do I page if checkout-api fails?") == "multi"
    assert heuristic_kind("How much memory does Redis have?") == "single"


def test_extractive_flow_end_to_end(retriever):
    flow = build_flow(retriever, llm=None)
    out = ask(flow, "How many SMS does the notifications worker send per day?")
    assert out["mode"] == "extractive"
    assert "90,000" in out["answer"]
    assert out["citations"] and out["grounded"] is True
    assert out["trace"][0].startswith("classify") and any("self_check" in t for t in out["trace"])


def test_flow_routes_multi_hop_to_graph(retriever):
    out = ask(build_flow(retriever, None), "Who is the primary on-call engineer for checkout-api?")
    assert out["kind"] == "multi" and out["retriever"] == "graph"
    assert "Nabil Ferhat" in " ".join(c.text for c in out["result"].chunks)


def test_forced_retriever(retriever):
    out = ask(build_flow(retriever, None), "Who owns redis-cache?", retriever="vector")
    assert out["retriever"] == "vector"


def test_ungrounded_answer_triggers_one_retry(retriever):
    class Liar:
        calls = 0

        def chat(self, system, user, temperature=0.0):
            if "Classify" in system:
                return "single"
            if "supported by the context" in system:
                return "no"
            Liar.calls += 1
            return "The moon is made of cheese."

    out = ask(build_flow(retriever, Liar()), "How long does a full rebuild of the search index take?")
    assert Liar.calls == 2 and out["grounded"] is False
    assert out["trace"].count("retrieve: graph k=10") == 1


def test_lexical_groundedness():
    res = RetrievalResult("vector", [RetrievedChunk("c", "d", "Sentinel promotes the replica within 30 seconds.", 1.0)])
    assert lexical_grounded("Sentinel promotes the replica within 30 seconds", res)
    assert not lexical_grounded("Elephants wear purple hats daily", res)


class FakeRetriever:
    """Stands in for the Neo4j-backed retriever so the flow logic runs without a database."""

    def __init__(self, text: str):
        self.chunk = RetrievedChunk("DOC-1#0.0", "DOC-1", text, 1.0)
        self.calls: list[tuple[str, int]] = []

    def retrieve(self, question, retriever="hybrid", k=None):
        self.calls.append((retriever, k))
        return RetrievalResult(retriever, [self.chunk])

    def with_evidence(self, question, result):
        return result


def test_flow_without_database_answers_and_cites():
    fake = FakeRetriever("Calls to the card processor time out after 8 seconds and are retried once.")
    out = ask(build_flow(fake, llm=None), "After how many seconds do calls to the card processor time out?", k=3)
    assert out["mode"] == "extractive" and out["grounded"] is True
    assert "8 seconds" in out["answer"] and out["citations"] == ["DOC-1#0.0"]
    assert fake.calls == [("vector", 3)]


def test_flow_retries_once_with_graph_when_ungrounded():
    class Liar:
        def chat(self, system, user, temperature=0.0):
            return "single" if "Classify" in system else ("no" if "supported by" in system else "Invented claim.")

    fake = FakeRetriever("Redis has 16 GB of memory.")
    out = ask(build_flow(fake, Liar()), "How much memory does Redis have?", k=4)
    assert fake.calls == [("vector", 4), ("graph", 8)]
    assert out["grounded"] is False and out["mode"] == "llm"


def test_answer_step_reads_the_evidence_chunks():
    class Recorder:
        prompts: list[str] = []

        def chat(self, system, user, temperature=0.0):
            Recorder.prompts.append(user)
            return (
                "single"
                if "Classify" in system
                else ("yes" if "supported by" in system else "Restart the replica [RB-1#1.0].")
            )

    class WithEvidence(FakeRetriever):
        def with_evidence(self, question, result):
            body = RetrievedChunk("RB-1#1.0", "RB-1", "Never restart the primary; fail over first.", 0.5, "evidence")
            return RetrievalResult(result.retriever, result.chunks + [body], result.paths, result.seeds)

    out = ask(
        build_flow(WithEvidence("Runbook RB-1 owner: TEAM-PLATFORM."), Recorder()), "How do I restart redis?", k=1
    )
    answer_prompt = next(p for p in Recorder.prompts if p.startswith("Question:"))
    assert "[RB-1#1.0] Never restart the primary" in answer_prompt
    assert out["citations"] == ["RB-1#1.0"]
    assert "evidence: +1 chunks" in out["trace"]
