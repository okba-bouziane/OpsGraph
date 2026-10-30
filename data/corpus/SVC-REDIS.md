# Service: redis-cache
*Sample data, fictional.*

Document ID: SVC-REDIS
Type: Service
Kind: Cache
Owner: TEAM-PLATFORM
Alerts: RedisDown, RedisMemoryHigh
Tier: 1

## What it is
Redis 7 used for carts, page caching and session caching. Since April 2025 it runs as a primary with one replica and Redis Sentinel, which promotes the replica automatically when the primary fails.

## Limits
The primary has 16 GB of memory. RedisMemoryHigh fires above 85% memory use; at 100%, Redis starts evicting keys, and carts can be lost.
