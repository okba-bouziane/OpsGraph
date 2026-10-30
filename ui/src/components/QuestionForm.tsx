import { useState, type FormEvent, type KeyboardEvent } from "react";

import { RETRIEVER_OPTIONS, SAMPLES } from "../config";
import type { Retriever } from "../types";

interface Props {
  loading: boolean;
  onAsk: (question: string, retriever: Retriever) => void;
}

/** Question box, retriever picker, Ask button and the sample questions. */
export function QuestionForm({ loading, onAsk }: Props) {
  const [question, setQuestion] = useState("");
  const [retriever, setRetriever] = useState<Retriever>("auto");

  const send = (text: string) => {
    if (text.trim() && !loading) onAsk(text, retriever);
  };

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    send(question);
  };

  // Enter asks, Shift+Enter adds a new line.
  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      send(question);
    }
  };

  const askSample = (text: string) => {
    setQuestion(text);
    send(text);
  };

  return (
    <>
      <form id="form" onSubmit={onSubmit}>
        <textarea
          id="q"
          rows={3}
          required
          placeholder="Ask like an on-call engineer, e.g. who do I page if checkout-api fails?"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={onKeyDown}
        />
        <div className="row">
          <span className="hint">
            <kbd>Enter</kbd> to ask, <kbd>Shift</kbd>+<kbd>Enter</kbd> for a new line
          </span>
          <select
            id="retriever"
            aria-label="Retriever"
            value={retriever}
            onChange={(e) => setRetriever(e.target.value as Retriever)}
          >
            {RETRIEVER_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
          <button className="primary" type="submit" disabled={loading}>
            {loading ? (
              <>
                <span className="spinner" aria-hidden="true" />
                Asking
              </>
            ) : (
              "Ask"
            )}
          </button>
        </div>
      </form>
      <p className="samples-title">Try a sample question</p>
      <div className="chips" id="chips">
        {SAMPLES.map((text) => (
          <button key={text} type="button" className="chip" onClick={() => askSample(text)}>
            {text}
          </button>
        ))}
      </div>
    </>
  );
}
