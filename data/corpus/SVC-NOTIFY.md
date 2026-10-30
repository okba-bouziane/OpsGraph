# Service: notifications-worker
*Sample data, fictional.*

Document ID: SVC-NOTIFY
Type: Service
Kind: Worker
Owner: TEAM-ORDERS
Depends on: SVC-EVENTS (consumes order and delivery events)
Alerts: SmsQueueBacklog
Tier: 3

## What it does
Sends SMS messages to customers: order confirmed, out for delivery, delivered. It sends about 90,000 SMS per day through a local SMS provider, in Arabic or French depending on the customer's choice.

## Failure modes
Messages wait in the notifications queue on the events bus. SmsQueueBacklog fires when more than 20,000 messages are waiting.
