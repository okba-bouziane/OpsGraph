# Service: numidia-pay
*Sample data, fictional.*

Document ID: SVC-NUMIDIAPAY
Type: Service
Kind: External provider
Owner: TEAM-PAY
Alerts: NumidiaPayCertificateExpiry
Tier: 1

## What it is
Numidia Pay is the external card processor for CIB and Edahabia cards. Tassili Market connects to it over mutual TLS, so both sides present a certificate.

## Contacts
The processor's support desk answers 24/7 on its incident line. The integration contract promises 99.9% monthly availability.

## Certificates
Our client certificate for Numidia Pay is valid for one year. NumidiaPayCertificateExpiry fires 30 days before it expires.
