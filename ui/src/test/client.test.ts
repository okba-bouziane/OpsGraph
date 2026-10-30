import { afterEach, describe, expect, it, vi } from "vitest";

import { ask, getEntity } from "../api/client";

afterEach(() => vi.unstubAllGlobals());

function mockFetch(status: number, body: unknown) {
  const fn = vi.fn().mockResolvedValue({
    ok: status < 400,
    status,
    statusText: "Bad Gateway",
    json: () => Promise.resolve(body),
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

describe("api client", () => {
  it("posts the question and retriever as JSON", async () => {
    const fetch = mockFetch(200, { answer: "ok" });
    await ask("Who is on call for checkout-api?", "graph");
    const [url, init] = fetch.mock.calls[0];
    expect(url).toBe("http://localhost:8001/ask");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ question: "Who is on call for checkout-api?", retriever: "graph" });
  });

  it("raises the API's error detail", async () => {
    mockFetch(502, { detail: "query failed: neo4j down" });
    await expect(ask("Who is on call for checkout-api?", "auto")).rejects.toThrow("query failed: neo4j down");
  });

  it("falls back to the status text when the error body is not JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, statusText: "Bad Gateway", json: () => Promise.reject(new Error()) }),
    );
    await expect(getEntity("SVC-CHECKOUT")).rejects.toThrow("Bad Gateway");
  });

  it("encodes entity names in the URL", async () => {
    const fetch = mockFetch(200, {});
    await getEntity("Nabil Ferhat");
    expect(fetch.mock.calls[0][0]).toBe("http://localhost:8001/graph/entity/Nabil%20Ferhat");
  });
});
