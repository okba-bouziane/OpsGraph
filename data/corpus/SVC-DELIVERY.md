# Service: delivery-tracker
*Sample data, fictional.*

Document ID: SVC-DELIVERY
Type: Service
Kind: Worker
Owner: TEAM-ORDERS
Depends on: SVC-EVENTS (consumes order events); SVC-ORDERS (order details)
Alerts: DeliveryStatusLag
Tier: 2

## What it does
Hands new orders to courier partners and polls them for status updates (picked up, in transit, delivered, returned). It covers all 58 wilayas through three courier partners.

## Failure modes
If the events bus backs up, new orders reach couriers late. DeliveryStatusLag fires when status updates are more than 2 hours behind.
