# Service: checkout-api
*Sample data, fictional.*

Document ID: SVC-CHECKOUT
Type: Service
Kind: API
Owner: TEAM-PAY
Depends on: SVC-PAYMENTS (critical); SVC-ORDERS (critical); SVC-AUTH (critical); SVC-REDIS (cart storage)
Alerts: CheckoutHighErrorRate, CheckoutSlowP95
Tier: 1

## What it does
Turns a cart into an order: checks the customer's session, validates stock and delivery address, asks payments-gateway to charge the card or records cash on delivery, then asks orders-service to create the order.

## Failure modes
Carts are stored in Redis. If Redis is unavailable, customers lose their carts and checkout fails. Cash-on-delivery orders do not need the payments gateway, so they keep working during a card payment outage.

## Targets
CheckoutHighErrorRate fires when more than 2% of checkout requests return a 5xx error for 5 minutes. The 95th percentile latency target is 1.5 seconds.
