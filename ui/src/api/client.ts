// Calls to the OpsGraph FastAPI service.

import { API_BASE } from "../config";
import type { AskResponse, EntityDetail, Health, Retriever } from "../types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(API_BASE + path, init);
  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(body.detail || res.statusText);
  }
  return (await res.json()) as T;
}

/** GET /health: Neo4j status, graph counts and the configured model. */
export const getHealth = () => request<Health>("/health");

/** POST /ask: answer, citations, graph paths and the subgraph for one question. */
export const ask = (question: string, retriever: Retriever) =>
  request<AskResponse>("/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, retriever }),
  });

/** GET /graph/entity/{name}: one entity and its neighbours. */
export const getEntity = (id: string) => request<EntityDetail>("/graph/entity/" + encodeURIComponent(id));
