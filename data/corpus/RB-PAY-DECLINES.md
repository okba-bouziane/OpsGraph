# Runbook: Card payment declines spike
*Sample data, fictional.*

Document ID: RB-PAY-DECLINES
Type: Runbook
Service: SVC-PAYMENTS
Alerts: PaymentDeclineRateHigh, PaymentTimeouts
Updated: 2025-09-02

## Symptoms
Many customers see "payment refused" at checkout while their cards are fine. The decline rate goes above 15%.

## Steps
1. Open the payments dashboard and check whether declines come from one card type (CIB or Edahabia) or all of them.
2. Check the Numidia Pay status page and the certificate expiry date of our client certificate.
3. If the processor is at fault, switch checkout to "cash on delivery only" with the feature flag card-payments-enabled=false. This keeps sales going.
4. Call the Numidia Pay incident line and open a ticket.

## Escalate
If card payments have been failing for more than 15 minutes, page the Checkout & Payments escalation contact.
