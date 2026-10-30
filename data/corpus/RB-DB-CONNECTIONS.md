# Runbook: main-db running out of connections
*Sample data, fictional.*

Document ID: RB-DB-CONNECTIONS
Type: Runbook
Service: SVC-MAINDB
Alerts: MainDbConnectionsHigh, OrdersDbPoolExhausted
Updated: 2025-10-21

## Symptoms
Services time out on database calls. The connection count on the primary goes above 320.

## Steps
1. Find which service holds the connections with the connection report query (grouped by application name).
2. Since October 2025 every service connects through PgBouncer; check that no service bypasses it.
3. Kill idle transactions older than 5 minutes.
4. Do not raise max_connections above 400 without the Platform lead.
