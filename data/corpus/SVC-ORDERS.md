# Service: orders-service
*Sample data, fictional.*

Document ID: SVC-ORDERS
Type: Service
Kind: API
Owner: TEAM-ORDERS
Depends on: SVC-MAINDB (critical); SVC-EVENTS (order events)
Alerts: OrdersErrorRate, OrdersDbPoolExhausted
Tier: 1

## What it does
Creates and stores orders, and publishes order.created and order.cancelled events that the delivery tracker and the notifications worker consume.

## Failure modes
Orders are stored in the orders schema of main-db. The service holds a pool of 40 database connections. OrdersDbPoolExhausted fires when all connections are busy for more than 1 minute.
