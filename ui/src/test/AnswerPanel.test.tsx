import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AnswerPanel, cleanAnswer } from "../components/AnswerPanel";
import type { AskResponse } from "../types";

const result: AskResponse = {
  question: "Who is the primary on-call engineer for checkout-api?",
  answer: "Page **Nabil Ferhat** 【ONC-PAY#0.0】.",
  mode: "llm",
  kind: "multi",
  retriever: "graph",
  grounded: true,
  citations: [{ chunk_id: "ONC-PAY#0.0", doc_id: "ONC-PAY", text: "x".repeat(300), score: 0.91, via: "graph" }],
  cited_ids: ["ONC-PAY#0.0"],
  paths: [{ text: "SVC-CHECKOUT -[OWNED_BY]-> TEAM-PAY <-[COVERS]- ONC-PAY", nodes: ["SVC-CHECKOUT", "TEAM-PAY", "ONC-PAY"], edges: [] }],
  subgraph: { nodes: [], edges: [] },
  trace: [],
};

describe("AnswerPanel", () => {
  it("removes markdown bold and normalises the CJK brackets", () => {
    expect(cleanAnswer(result.answer)).toBe("Page Nabil Ferhat [ONC-PAY#0.0].");
  });

  it("turns narrow no-break spaces into normal spaces and separates a glued citation", () => {
    expect(cleanAnswer("Sentinel\u202Fpromotes the\u00A0replica[RB-REDIS-FAILOVER#2.0].")).toBe(
      "Sentinel promotes the replica [RB-REDIS-FAILOVER#2.0].",
    );
  });

  it("separates a citation glued to a closing quote", () => {
    expect(cleanAnswer('says "never restart the primary"[RB-REDIS-FAILOVER#2.0].')).toBe('says "never restart the primary" [RB-REDIS-FAILOVER#2.0].');
  });

  it("shows the tags, the answer, the path and a shortened citation", () => {
    render(<AnswerPanel result={result} />);
    expect(screen.getByText("multi-hop")).toBeTruthy();
    expect(screen.getByText("grounded").className).toContain("ok");
    expect(screen.getByText(/Nabil Ferhat/)).toBeTruthy();
    expect(document.querySelector(".path")!.textContent).toBe("SVC-CHECKOUT -[OWNED_BY]-> TEAM-PAY <-[COVERS]- ONC-PAY");
    expect(document.querySelector(".path .rel")!.textContent).toBe("-[OWNED_BY]->");
    expect(document.querySelector(".cite")!.textContent).toContain("x".repeat(260) + "...");
  });

  it("says when no graph path was used", () => {
    render(<AnswerPanel result={{ ...result, paths: [], grounded: false }} />);
    expect(screen.getByText("none (vector retrieval)")).toBeTruthy();
    expect(screen.getByText("not grounded").className).toContain("warn");
  });
});
