# Service: main-db
*Sample data, fictional.*

Document ID: SVC-MAINDB
Type: Service
Kind: Database
Owner: TEAM-PLATFORM
Alerts: MainDbConnectionsHigh, MainDbReplicationLag
Tier: 0

## What it is
The main PostgreSQL 16 cluster: one primary and two replicas. It holds the orders, catalog, payments and accounts schemas.

## Limits
The primary accepts at most 400 connections. MainDbConnectionsHigh fires above 320 connections (80%). Replication lag above 30 seconds fires MainDbReplicationLag.

## Backups
Full backup every night at 01:00, write-ahead logs archived every 5 minutes, kept for 14 days.
