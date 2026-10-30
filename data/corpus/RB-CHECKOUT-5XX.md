# Runbook: Checkout returns server errors
*Sample data, fictional.*

Document ID: RB-CHECKOUT-5XX
Type: Runbook
Service: SVC-CHECKOUT
Alerts: CheckoutHighErrorRate
Updated: 2025-07-20

## Symptoms
More than 2% of checkout requests fail with a 5xx error.

## Steps
1. Look at which dependency fails in the checkout traces: payments-gateway, orders-service, auth-service or redis-cache.
2. If the errors are payment errors, follow RB-PAY-DECLINES.
3. If Redis errors appear ("connection refused" on carts), follow RB-REDIS-FAILOVER.
4. If the last deploy was less than 1 hour ago, roll it back first and investigate after.
