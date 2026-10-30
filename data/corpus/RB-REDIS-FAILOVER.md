# Runbook: Redis failover
*Sample data, fictional.*

Document ID: RB-REDIS-FAILOVER
Type: Runbook
Service: SVC-REDIS
Alerts: RedisDown, RedisMemoryHigh
Supersedes: RB-REDIS-RESTART
Updated: 2025-04-18

## Symptoms
Services log "connection refused" or "READONLY" errors from Redis. Carts disappear for customers.

## Steps
1. Check Sentinel: it should have promoted the replica within 30 seconds. Run the sentinel status command from the ops box.
2. If Sentinel did not fail over, force it with a manual failover command.
3. If memory is above 85%, find the largest keys and check the page cache settings before anything else.
4. Never restart the primary while it is the only healthy node.

## Escalate
Page the Platform escalation contact if Redis is not healthy after 15 minutes.
