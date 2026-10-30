// Settings shared by the UI.

// API base URL: ?api=... in the page URL, then VITE_API_URL at build time, then the local default.
export const API_BASE =
  new URLSearchParams(window.location.search).get("api") ||
  import.meta.env.VITE_API_URL ||
  "http://localhost:8001";

// Node colours in the graph view, one per entity type.
export const COLORS: Record<string, string> = {
  Service: "#2457d6",
  Team: "#157347",
  Rota: "#0e7490",
  Runbook: "#b45309",
  Postmortem: "#c2410c",
  Decision: "#8a3ffc",
  Person: "#657080",
  Alert: "#be123c",
};

// Clickable example questions under the form.
export const SAMPLES = [
  "Who is the primary on-call engineer for checkout-api?",
  "PaymentDeclineRateHigh fired. Which runbook applies, and who is the escalation contact?",
  "What breaks if main-db goes down?",
  "What was decided after the card payment outage of August 2025?",
  "Which team owns the service that caused the Ramadan sale outage?",
];

export const RETRIEVER_OPTIONS = [
  { value: "auto", label: "auto (flow chooses)" },
  { value: "vector", label: "vector only" },
  { value: "graph", label: "graph-augmented" },
  { value: "hybrid", label: "hybrid" },
] as const;

// Neighbour types left out of the node detail (many of them, not useful for navigation).
export const HIDDEN_NEIGHBOUR_TYPES = ["ActionItem", "Date"];
export const MAX_NEIGHBOURS = 14;
export const CITATION_PREVIEW = 260;
