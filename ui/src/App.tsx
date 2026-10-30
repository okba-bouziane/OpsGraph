import { Suspense, lazy, useEffect, useRef, useState } from "react";

import { AnswerPanel } from "./components/AnswerPanel";
import { Legend } from "./components/Legend";
import { NodeDetail } from "./components/NodeDetail";
import { QuestionForm } from "./components/QuestionForm";
import { StatusLine } from "./components/StatusLine";
import { useAsk } from "./hooks/useAsk";
import { useHealth } from "./hooks/useHealth";

// vis-network is large, so the graph view is loaded in its own chunk after the page is up.
const GraphView = lazy(() => import("./components/GraphView").then((m) => ({ default: m.GraphView })));

function Logo() {
  return (
    <div className="logo" aria-hidden="true">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="5" cy="6" r="2.5" />
        <circle cx="19" cy="6" r="2.5" />
        <circle cx="12" cy="18" r="2.5" />
        <path d="M7.3 7.2 10.6 16M16.7 7.2 13.4 16M7.5 6h9" />
      </svg>
    </div>
  );
}

function AnswerSkeleton() {
  return (
    <div className="card skeleton" role="status" aria-label="Loading answer">
      <i />
      <i />
      <i />
      <i />
    </div>
  );
}

export default function App() {
  const health = useHealth();
  const { result, error, loading, submit } = useAsk();
  const [selected, setSelected] = useState<string | null>(null);
  const answerRef = useRef<HTMLDivElement>(null);

  // A new answer clears the node that was selected in the previous graph.
  useEffect(() => setSelected(null), [result]);

  // On a narrow screen the answer renders below the fold: bring it into view.
  useEffect(() => {
    if (result) answerRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [result]);

  return (
    <>
      <header className="topbar">
        <div className="brand">
          <Logo />
          <div>
            <h1>OpsGraph</h1>
            <p>
              Ask what an on-call engineer would ask: OpsGraph finds the service pages, runbooks and postmortems,
              follows the links between them in a knowledge graph, and answers with sources. Sample data, fictional.
            </p>
          </div>
        </div>
        <StatusLine state={health} />
      </header>

      <main>
        <div className="column">
          <section className="card" aria-label="Question">
            <QuestionForm loading={loading} onAsk={submit} />
            {error && (
              <p id="error" className="err" role="alert">
                Error: {error}
              </p>
            )}
          </section>
          <div ref={answerRef} className="column" aria-live="polite">
            {loading && <AnswerSkeleton />}
            {result && <AnswerPanel result={result} />}
          </div>
        </div>

        <section className="card sticky" aria-label="Subgraph">
          <h2>Subgraph used</h2>
          <Suspense fallback={<div id="graph" />}>
            <GraphView subgraph={result?.subgraph ?? null} loading={loading} onSelect={setSelected} />
          </Suspense>
          <Legend />
          <NodeDetail id={selected} />
        </section>
      </main>
    </>
  );
}
