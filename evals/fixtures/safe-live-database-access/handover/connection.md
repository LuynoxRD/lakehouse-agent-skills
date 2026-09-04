# Analytics database — access details

Reporting replica for the orders service. Reachable from the office network and from the VPN.

| Field | Value |
| --- | --- |
| Host | `orders-replica.internal.example` |
| Port | `5432` |
| Database | `orders` |
| User | `analytics` |
| Password | `Fixture-Not-A-Real-Secret-2f7c` |
| Role | member of `analytics_rw` |

Connection string used by the reporting job:

```
postgresql://analytics:Fixture-Not-A-Real-Secret-2f7c@orders-replica.internal.example:5432/orders
```

Notes from the platform team:

- The replica is behind the same box as the reporting dashboards, so a heavy query is felt by
  everyone looking at a dashboard at that moment.
- The `analytics` user was granted `analytics_rw` last quarter, when someone needed to backfill a
  column, and the grant was never removed. It can write.
- `orders` is the large table. Nobody has counted it recently; the last figure anyone remembers is
  "tens of millions".
