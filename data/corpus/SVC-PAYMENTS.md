# Service: payments-gateway
*Sample data, fictional.*

Document ID: SVC-PAYMENTS
Type: Service
Kind: API
Owner: TEAM-PAY
Depends on: SVC-NUMIDIAPAY (critical for card payments); SVC-MAINDB (payment records); SVC-EVENTS (payment events)
Alerts: PaymentDeclineRateHigh, PaymentTimeouts
Tier: 1

## What it does
Charges CIB and Edahabia cards through the processor Numidia Pay and records every payment attempt. It never stores card numbers: Numidia Pay returns a token.

## Failure modes
Calls to Numidia Pay time out after 8 seconds and are retried once. PaymentDeclineRateHigh fires when more than 15% of card payments are declined over 10 minutes, which usually means a problem at the processor rather than with customers' cards. PaymentTimeouts fires when more than 3% of calls time out.
