# OpsGraph web UI

React 19 + Vite + TypeScript. Built to static files and served by nginx (port 8090 in `docker compose`).

```bash
npm install
npm run dev         # http://localhost:5174, talks to the API on http://localhost:8001
npm test            # Vitest
npm run build       # typecheck + production build into dist/
```

```
src/
├── main.tsx                 mounts <App />
├── App.tsx                  page layout; the graph view is lazy-loaded (vis-network is large)
├── config.ts                API URL, node colours, sample questions, limits
├── types.ts                 types of the API responses (/health, /ask, /graph/entity)
├── api/client.ts            fetch wrapper with error handling
├── hooks/
│   ├── useHealth.ts         loads /health once
│   └── useAsk.ts            sends a question, keeps result / error / loading
├── components/
│   ├── StatusLine.tsx       header badges: Neo4j, graph size, model
│   ├── QuestionForm.tsx     question box (Enter to ask), retriever picker, sample questions
│   ├── AnswerPanel.tsx      tags, answer, graph paths, citation cards
│   ├── RelationText.tsx     highlights -[RELATION]-> in paths
│   ├── GraphView.tsx        subgraph drawn with vis-network
│   ├── NodeDetail.tsx       neighbours of the clicked node
│   └── Legend.tsx           colour key
├── styles.css               theme tokens (light and dark), layout, components
└── test/                    Vitest + Testing Library
```

The API URL comes from `?api=...` in the page URL, then `VITE_API_URL` at build time, then `http://localhost:8001`.
The element ids `q`, `retriever`, `out` and the `button.primary` Ask button are used by `scripts/demo.cjs`; keep them if you change the markup.
