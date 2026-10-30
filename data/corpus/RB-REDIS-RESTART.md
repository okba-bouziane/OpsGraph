# Runbook: Restart Redis (old)
*Sample data, fictional.*

Document ID: RB-REDIS-RESTART
Type: Runbook
Service: SVC-REDIS
Alerts: RedisDown
Updated: 2024-11-05
Status: Replaced by RB-REDIS-FAILOVER

## Steps
1. SSH to the single Redis host and restart the redis service.
2. Wait for the cache to warm up (about 10 minutes).

This runbook dates from when Redis ran on a single host. It no longer applies.
