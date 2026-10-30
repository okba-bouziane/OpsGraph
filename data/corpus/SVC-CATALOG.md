# Service: catalog-service
*Sample data, fictional.*

Document ID: SVC-CATALOG
Type: Service
Kind: API
Owner: TEAM-DISCOVERY
Depends on: SVC-MAINDB (critical); SVC-EVENTS (publishes product changes)
Alerts: CatalogErrorRate
Tier: 1

## What it does
Stores products, prices, stock levels shown to customers, and seller information. Sellers update their products through the seller portal, which calls this service.

## Failure modes
The catalog keeps its data in the catalog schema of main-db. Without the database it cannot serve product pages. Publishing product changes to the events bus is asynchronous: if the bus is down, changes are kept in an outbox table and sent later.
