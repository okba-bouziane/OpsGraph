// Shapes of the OpsGraph API responses (see opsgraph/api.py).

export type Retriever = "auto" | "vector" | "graph" | "hybrid";

export interface Health {
  status: "ok" | "degraded";
  neo4j: boolean;
  graph: { nodes?: number; chunks?: number; entities?: number; relationships?: number };
  llm_configured: boolean;
  llm_model: string | null;
  embedding_model: string;
}

export interface Citation {
  chunk_id: string;
  doc_id: string;
  text: string;
  score: number;
  via: string;
}

export interface GraphPath {
  text: string;
  nodes: string[];
  edges: { type: string; source: string; target: string }[];
}

export interface SubgraphNode {
  id: string;
  name: string;
  type: string;
  title?: string | null;
  retrieved: boolean;
}

export interface SubgraphEdge {
  type: string;
  source: string;
  target: string;
  role?: string | null;
}

export interface Subgraph {
  nodes: SubgraphNode[];
  edges: SubgraphEdge[];
}

export interface AskResponse {
  question: string;
  answer: string;
  mode: "llm" | "extractive";
  kind: "single" | "multi";
  retriever: string;
  grounded: boolean;
  citations: Citation[];
  cited_ids: string[];
  paths: GraphPath[];
  subgraph: Subgraph;
  trace: string[];
}

export interface Neighbour {
  relation: string;
  outgoing: boolean;
  role: string | null;
  id: string;
  name: string;
  type: string;
}

export interface EntityDetail {
  id: string;
  type: string;
  properties: Record<string, unknown> & { title?: string };
  neighbours: Neighbour[];
}
