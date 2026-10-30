# Eval report (rule-based extractor)

Sample data, fictional. k = 5 chunks. 39 labelled questions.

## All questions

| Retriever | n | recall@5 | full@5 | MRR | fact@5 |
|---|---|---|---|---|---|
| vector | 39 | 0.799 | 0.667 | 0.818 | 0.667 |
| graph | 39 | 0.936 | 0.872 | 0.876 | 0.667 |
| hybrid | 39 | 0.846 | 0.667 | 0.843 | 0.564 |

## Single-hop

| Retriever | n | recall@5 | full@5 | MRR | fact@5 |
|---|---|---|---|---|---|
| vector | 16 | 1.000 | 1.000 | 0.938 | 1.000 |
| graph | 16 | 1.000 | 1.000 | 0.938 | 0.938 |
| hybrid | 16 | 1.000 | 1.000 | 0.938 | 1.000 |

## Multi-hop

| Retriever | n | recall@5 | full@5 | MRR | fact@5 |
|---|---|---|---|---|---|
| vector | 23 | 0.659 | 0.435 | 0.736 | 0.435 |
| graph | 23 | 0.891 | 0.783 | 0.833 | 0.478 |
| hybrid | 23 | 0.739 | 0.435 | 0.777 | 0.261 |

