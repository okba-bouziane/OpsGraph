"""LangGraph query flow:

    classify -> choose_retriever -> retrieve -> answer -> self_check --(ungrounded, first try)--> retrieve
                                                                      \\--> END

With an LLM configured, classify/answer/self_check call it. Without one, classification is a
heuristic, the answer is extractive (the best-matching sentences, cited) and the groundedness
check is lexical. `mode` in the output says which path ran.
"""

import re
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from opsgraph import config
from opsgraph.llm import LLMClient
from opsgraph.retrieval import RetrievalResult, Retriever, unique

MULTI_HINTS = re.compile(
    r"\b(page|paged|on[- ]call|who|owns?|owner|owned|depends?|dependen\w*|affect\w*|breaks?|blast|impact\w*|"
    r"goes down|caused?|root cause|decided|decision|follow[- ]ups?|after (the|an?)|replaced|supersed\w*|"
    r"escalat\w*|alert|fired|which team|runbook for)\b",
    re.I,
)
META_LINE = re.compile(
    r"^(Document ID|Type|Kind|Owner|Depends on|Alerts|Tier|Members|Channel|Covers|Primary|Secondary|Escalation|"
    r"Service|Updated|Status|Supersedes|References|Date|Severity|Root cause|Impacted|Follow-ups|Duration|Applies to):"
)
STOP = set(
    "the a an of to and or in on for by is are was were be it its that this with as at from what who "
    "which how when must shall under any each".split()
)


CLASSIFY_PROMPT = (
    "Classify the operations question. Reply with exactly one word: 'single' if one document "
    "answers it, 'multi' if it needs facts from several linked documents (dependencies, owners, "
    "on-call rotas, runbooks, incidents and the decisions that followed)."
)
ANSWER_PROMPT = (
    "Answer the on-call engineer's question using ONLY the context. Be short and practical. Cite "
    "the chunk ids in square brackets after each claim, e.g. [SVC-CHECKOUT#2.0]. Use the graph "
    "paths to connect documents (service -> owner team -> on-call rota). Give names, ids, numbers and "
    "commands exactly as the context writes them (for example the person to page, the service id, the "
    "rule a runbook states). If the context does not contain the answer, say so."
)
CHECK_PROMPT = "Reply 'yes' if every claim in the answer is supported by the context, otherwise 'no'. One word."
CITATION_RE = re.compile(r"[\[【]([A-Za-z0-9-]+#\d+\.\d+)[\]】]")  # models sometimes emit 【 】 brackets


class FlowState(TypedDict, total=False):
    question: str
    forced_retriever: str | None
    k: int
    kind: str
    retriever: str
    result: RetrievalResult
    answer: str
    citations: list[str]
    grounded: bool
    attempts: int
    mode: str
    trace: list[str]


def tokens(text: str) -> set[str]:
    return {t[:6] for t in re.findall(r"[a-z0-9%,.]+", text.lower()) if t not in STOP and len(t) > 1}


def heuristic_kind(question: str) -> str:
    return "multi" if len(MULTI_HINTS.findall(question)) >= 1 else "single"


def extractive_answer(question: str, result: RetrievalResult, n: int = 2) -> tuple[str, list[str]]:
    """Pick the n sentences with most question-word overlap from the retrieved chunks.

    A metadata line ("Primary: Kamel Benyahia") is a candidate only when the question uses its field
    name ("primary", "owner", "escalation"): the value is usually a name the question cannot contain."""
    q = tokens(question)
    cands = []
    for c in result.chunks:
        for sent in re.split(r"(?<=[.!?])\s+|\n+", c.text):
            raw, sent = sent.strip(), sent.strip(" #*")
            if raw.startswith(("[", "#", "*")):
                continue
            if META_LINE.match(raw):
                if q & tokens(raw.split(":")[0]):
                    cands.append((1.0, sent, c.chunk_id))
            elif len(sent) > 25:
                cands.append((len(q & tokens(sent)) / (1 + len(tokens(sent)) ** 0.5), sent, c.chunk_id))
    cands.sort(key=lambda x: x[0], reverse=True)
    top = cands[:n]
    return " ".join(f"{s} [{cid}]" for _, s, cid in top), [cid for _, _, cid in top]


def lexical_grounded(answer: str, result: RetrievalResult, threshold: float = 0.6) -> bool:
    ans = tokens(re.sub(r"\[[^\]]+\]", "", answer))
    ctx = tokens(" ".join(c.text for c in result.chunks))
    return bool(ans) and len(ans & ctx) / len(ans) >= threshold


def classify_with_llm(llm: LLMClient, question: str) -> str | None:
    """'single' or 'multi' from the model, or None if the call fails (caller falls back to the heuristic)."""
    try:
        return "multi" if "multi" in llm.chat(CLASSIFY_PROMPT, question).strip().lower() else "single"
    except Exception:
        return None


def answer_with_llm(llm: LLMClient, question: str, result: RetrievalResult) -> tuple[str, list[str]]:
    context = "\n\n".join(f"[{c.chunk_id}] {c.text}" for c in result.chunks)
    paths = "\n".join(p.describe() for p in result.paths) or "(none)"
    text = llm.chat(ANSWER_PROMPT, f"Question: {question}\n\nContext:\n{context}\n\nGraph paths:\n{paths}")
    return text, unique(CITATION_RE.findall(text))


def grounded_with_llm(llm: LLMClient, answer: str, result: RetrievalResult) -> bool:
    """Ask the model to verify the answer; fall back to the lexical check if the call fails."""
    context = "\n".join(c.text for c in result.chunks)
    try:
        verdict = llm.chat(CHECK_PROMPT, f"Context:\n{context}\n\nAnswer:\n{answer}")
    except Exception:
        return lexical_grounded(answer, result)
    return verdict.strip().lower().startswith("yes")


def build_flow(retriever: Retriever, llm: LLMClient | None = None, llm_check: bool = True):
    """Compile the LangGraph flow. `llm_check=False` keeps the groundedness check lexical (cheaper evals)."""

    def classify(state: FlowState) -> FlowState:
        kind = heuristic_kind(state["question"])
        if llm and not state.get("forced_retriever"):  # a forced retriever makes the label moot
            kind = classify_with_llm(llm, state["question"]) or kind
        return {"kind": kind, "attempts": 0, "trace": [f"classify: {kind}"]}

    def choose(state: FlowState) -> FlowState:
        name = state.get("forced_retriever") or ("graph" if state["kind"] == "multi" else "vector")
        return {"retriever": name, "trace": state["trace"] + [f"retriever: {name}"]}

    def retrieve(state: FlowState) -> FlowState:
        name, k = state["retriever"], state.get("k") or config.TOP_K
        if state["attempts"] > 0:  # retry once, wider, with the graph
            name, k = "graph", k * 2
        result = retriever.retrieve(state["question"], name, k)
        result = retriever.with_evidence(state["question"], result)
        extra = sum(c.via == "evidence" for c in result.chunks)
        return {
            "result": result,
            "retriever": name,
            "trace": state["trace"] + [f"retrieve: {name} k={k}", f"evidence: +{extra} chunks"],
        }

    def answer(state: FlowState) -> FlowState:
        if llm:
            text, cites = answer_with_llm(llm, state["question"], state["result"])
            mode = "llm"
        else:
            text, cites = extractive_answer(state["question"], state["result"])
            mode = "extractive"
        return {
            "answer": text,
            "citations": cites,
            "mode": mode,
            "attempts": state["attempts"] + 1,
            "trace": state["trace"] + [f"answer: {mode}"],
        }

    def self_check(state: FlowState) -> FlowState:
        if llm and llm_check:
            ok = grounded_with_llm(llm, state["answer"], state["result"])
        else:
            ok = lexical_grounded(state["answer"], state["result"])
        return {"grounded": ok, "trace": state["trace"] + [f"self_check: {'grounded' if ok else 'not grounded'}"]}

    def after_check(state: FlowState) -> str:
        return END if state["grounded"] or state["attempts"] >= config.MAX_ANSWER_ATTEMPTS else "retrieve"

    graph = StateGraph(FlowState)
    for name, fn in (
        ("classify", classify),
        ("choose", choose),
        ("retrieve", retrieve),
        ("answer", answer),
        ("self_check", self_check),
    ):
        graph.add_node(name, fn)
    graph.add_edge(START, "classify")
    graph.add_edge("classify", "choose")
    graph.add_edge("choose", "retrieve")
    graph.add_edge("retrieve", "answer")
    graph.add_edge("answer", "self_check")
    graph.add_conditional_edges("self_check", after_check, {END: END, "retrieve": "retrieve"})
    return graph.compile()


def ask(flow, question: str, retriever: str | None = None, k: int | None = None) -> FlowState:
    return flow.invoke({"question": question, "forced_retriever": retriever, "k": k or config.TOP_K})
