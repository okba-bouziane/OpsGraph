# Service: events-bus
*Sample data, fictional.*

Document ID: SVC-EVENTS
Type: Service
Kind: Message broker
Owner: TEAM-PLATFORM
Alerts: EventsQueueBacklog, EventsNodeDown
Tier: 1

## What it is
A RabbitMQ 3.13 cluster of 3 nodes. Services publish events (order.created, product.updated, payment.captured) and other services consume them from their own queues.

## Limits
EventsQueueBacklog fires when any queue holds more than 50,000 messages. Each queue keeps messages for 3 days at most.
