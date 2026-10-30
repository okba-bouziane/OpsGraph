# Runbook: Events bus backlog
*Sample data, fictional.*

Document ID: RB-EVENTS-BACKLOG
Type: Runbook
Service: SVC-EVENTS
Alerts: EventsQueueBacklog, SmsQueueBacklog
Updated: 2025-06-30

## Symptoms
A queue on the events bus keeps growing. SMS arrive late, delivery statuses lag and search results go stale.

## Steps
1. Find the growing queue in the RabbitMQ management page.
2. Check that its consumer is running; scale the consumer to 3 instances if it is just slow.
3. If a single bad message blocks the queue, move it to the dead-letter queue.
4. Old SMS (more than 6 hours) can be dropped: customers should not get "your order is confirmed" the next day.
