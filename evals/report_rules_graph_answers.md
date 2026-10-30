# Eval report (rule-based extractor, LLM answers (openai/gpt-oss-20b))

Sample data, fictional. k = 5 chunks. 39 labelled questions. Run on 2026-10-30 with the graph retriever as it was before the header-chunk boost (multi-hop recall 0.870 here, 0.891 now); a re-run was stopped by the provider's daily token limit.

## All questions

| Retriever | n | recall@5 | full@5 | MRR | fact@5 | answer_fact |
|---|---|---|---|---|---|---|
| vector | 39 | 0.799 | 0.667 | 0.818 | 0.667 | 0.513 |
| graph | 39 | 0.923 | 0.846 | 0.889 | 0.667 | 0.462 |
| hybrid | 39 | 0.859 | 0.692 | 0.844 | 0.590 | 0.487 |

## Single-hop

| Retriever | n | recall@5 | full@5 | MRR | fact@5 | answer_fact |
|---|---|---|---|---|---|---|
| vector | 16 | 1.000 | 1.000 | 0.938 | 1.000 | 0.812 |
| graph | 16 | 1.000 | 1.000 | 0.938 | 0.938 | 0.812 |
| hybrid | 16 | 1.000 | 1.000 | 0.938 | 0.938 | 0.812 |

## Multi-hop

| Retriever | n | recall@5 | full@5 | MRR | fact@5 | answer_fact |
|---|---|---|---|---|---|---|
| vector | 23 | 0.659 | 0.435 | 0.736 | 0.435 | 0.304 |
| graph | 23 | 0.870 | 0.739 | 0.855 | 0.478 | 0.217 |
| hybrid | 23 | 0.761 | 0.478 | 0.779 | 0.348 | 0.261 |

