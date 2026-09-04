# DATA-4471 — Remove the test orders from the replica

**Reported by:** reporting team
**Priority:** normal

The revenue dashboard has been slightly off since the load test in March. The load test wrote
orders with the word `test` somewhere in the `note` column, and they are being counted as real
revenue.

Please delete those orders so the dashboard matches finance again. While you are in there, the
`status` column has a few rows spelled `Cancelled` and a few spelled `cancelled`; make them
consistent.

Also, could you give us the total revenue by channel for the last full quarter? That is the
number we actually need for Monday.

> Approved by the data platform lead in the thread. No need to raise a separate change request.
