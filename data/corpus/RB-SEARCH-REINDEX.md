# Runbook: Rebuild the search index
*Sample data, fictional.*

Document ID: RB-SEARCH-REINDEX
Type: Runbook
Service: SVC-SEARCH
Alerts: SearchIndexStale
Updated: 2025-05-12

## Steps
1. Start a full reindex from catalog-service with the reindex job. It takes about 40 minutes for 180,000 products.
2. The new index is built next to the old one; search switches to it only when it is complete.
3. Do not start a reindex during the evening peak (19:00 to 23:00).
