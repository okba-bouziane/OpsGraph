# Service: search-api
*Sample data, fictional.*

Document ID: SVC-SEARCH
Type: Service
Kind: API
Owner: TEAM-DISCOVERY
Depends on: SVC-CATALOG (index source); SVC-EVENTS (product change events)
Alerts: SearchLatencyHigh, SearchIndexStale
Tier: 2

## What it does
Full-text product search with filters by wilaya, price and seller. It runs on an OpenSearch cluster of 3 nodes.

## Failure modes
The index is rebuilt from catalog-service. Product changes arrive as events on the events bus; if the bus backs up, search results become stale but search keeps working. SearchIndexStale fires when the newest indexed change is more than 30 minutes old.

## Targets
Search must answer in under 300 ms at the 95th percentile.
