# Service: auth-service
*Sample data, fictional.*

Document ID: SVC-AUTH
Type: Service
Kind: Identity provider
Owner: TEAM-PLATFORM
Depends on: SVC-MAINDB (user accounts); SVC-REDIS (session cache)
Alerts: AuthLoginFailures
Tier: 1

## What it does
Keycloak-based sign-in for customers, sellers and staff. It issues the tokens that checkout-api and the seller portal check.

## Failure modes
Sessions are cached in Redis for speed and stored in main-db. If Redis is down, sign-in still works but is slower. If main-db is down, nobody can sign in.
