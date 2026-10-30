import { useEffect, useRef, useState } from "react";
import { DataSet, Network, type Edge, type Node, type Options } from "vis-network/standalone";

import { COLORS } from "../config";
import type { Subgraph, SubgraphEdge, SubgraphNode } from "../types";

const FALLBACK_COLOR = "#888";

/** Tracks the OS light/dark setting so the graph is redrawn with matching colours. */
function useColorScheme(): boolean {
  const [dark, setDark] = useState(() => window.matchMedia("(prefers-color-scheme: dark)").matches);
  useEffect(() => {
    const query = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = (e: MediaQueryListEvent) => setDark(e.matches);
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);
  return dark;
}

/** Colours from the CSS theme, so the graph follows light and dark mode. */
function theme() {
  const css = getComputedStyle(document.documentElement);
  const v = (name: string) => css.getPropertyValue(name).trim();
  return { panel: v("--card-2"), mute: v("--mute"), ink: v("--ink") };
}

function toVisNode(n: SubgraphNode, t: ReturnType<typeof theme>): Node {
  const color = COLORS[n.type] || FALLBACK_COLOR;
  return {
    id: n.id,
    label: n.name,
    title: n.title || n.type,
    shape: n.type === "Person" || n.type === "Alert" ? "ellipse" : "box",
    margin: { top: 8, right: 12, bottom: 8, left: 12 },
    shapeProperties: { borderRadius: 8 },
    color: {
      background: color,
      border: n.retrieved ? t.ink : color,
      highlight: { background: color, border: t.ink },
      hover: { background: color, border: t.ink },
    },
    borderWidth: n.retrieved ? 3 : 1, // documents whose chunks were retrieved get a ring (theme ink, so it shows in light and dark)
    font: { color: "#fff", size: 14, face: "system-ui, sans-serif" },
    shadow: { enabled: true, color: "rgba(0,0,0,0.25)", size: 8, x: 0, y: 2 },
  };
}

function toVisEdge(e: SubgraphEdge, i: number, t: ReturnType<typeof theme>): Edge {
  return {
    id: i,
    from: e.source,
    to: e.target,
    label: e.type + (e.role ? ` (${e.role})` : ""),
    arrows: { to: { enabled: true, scaleFactor: 0.6 } },
    color: { color: t.mute, highlight: t.ink, hover: t.ink, opacity: 0.7 },
    width: 1.4,
    // The label sits above the line with a halo in the panel colour, so it never runs into the arrow.
    font: { size: 11, align: "top", color: t.mute, strokeWidth: 5, strokeColor: t.panel, face: "ui-monospace, monospace" },
    smooth: { enabled: true, type: "dynamic", roundness: 0.5 },
  };
}

const OPTIONS: Options = {
  physics: {
    solver: "forceAtlas2Based",
    forceAtlas2Based: { gravitationalConstant: -90, springLength: 190, springConstant: 0.05, avoidOverlap: 0.9 },
    stabilization: { iterations: 250 },
  },
  edges: { length: 210 },
  interaction: { hover: true, tooltipDelay: 150 },
  layout: { improvedLayout: true },
};

interface Props {
  subgraph: Subgraph | null;
  loading?: boolean;
  onSelect: (id: string) => void;
}

function LoadingState() {
  return (
    <div className="empty" role="status">
      <span className="spinner" aria-hidden="true" />
      Searching the graph...
    </div>
  );
}

function EmptyState({ noMatches }: { noMatches: boolean }) {
  return (
    <div className="empty">
      <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
        <circle cx="5" cy="6" r="2.5" />
        <circle cx="19" cy="6" r="2.5" />
        <circle cx="12" cy="18" r="2.5" />
        <path d="M7.3 7.2 10.6 16M16.7 7.2 13.4 16M7.5 6h9" />
      </svg>
      {noMatches
        ? "No entities were retrieved for this question."
        : "Ask a question to see the entities and relations behind the answer."}
    </div>
  );
}

/** The entities and relations behind the answer, drawn with vis-network. */
export function GraphView({ subgraph, loading = false, onSelect }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const scheme = useColorScheme();
  const hasNodes = !!subgraph && subgraph.nodes.length > 0;

  useEffect(() => {
    if (!subgraph || !hasNodes || !container.current) return;
    const t = theme();
    const network = new Network(
      container.current,
      {
        nodes: new DataSet<Node>(subgraph.nodes.map((n) => toVisNode(n, t))),
        edges: new DataSet<Edge>(subgraph.edges.map((e, i) => toVisEdge(e, i, t))),
      },
      OPTIONS,
    );
    network.once("stabilizationIterationsDone", () => network.fit({ animation: { duration: 400, easingFunction: "easeInOutQuad" } }));
    network.on("click", (params: { nodes: (string | number)[] }) => {
      if (params.nodes.length) onSelect(String(params.nodes[0]));
    });
    return () => network.destroy();
  }, [subgraph, hasNodes, scheme, onSelect]);

  let content = <EmptyState noMatches={!!subgraph} />;
  if (loading) content = <LoadingState />;
  else if (hasNodes) content = <div ref={container} className="canvas" />;
  return <div id="graph">{content}</div>;
}
