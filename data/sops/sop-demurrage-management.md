# SOP-007 — Demurrage and Detention Management

**Owner:** Operations · Cost Recovery Desk
**Last reviewed:** 2026-02-10
**Applies to:** Any shipment where demurrage (terminal storage) or detention (carrier container hire) charges have begun or will begin within 5 business days.

---

## Definitions

| Term | What it means | Who charges it |
|---|---|---|
| **Demurrage** | Storage of laden containers at the terminal beyond the free-time window | Terminal operator (passed through by carrier) |
| **Detention** | Use of carrier-owned containers beyond the free-time window outside the terminal (e.g., during cargo unloading at consignee site) | Carrier |
| **Per-diem** | Some carriers combine the two into a single per-day charge | Carrier |

The shipment record's `downstream_constraints.demurrage_starts_at` and `demurrage_rate_usd_per_day` cover the demurrage clock. Detention is typically not pre-flagged; calculate based on container hire terms.

## Free-time windows (typical)

| Region | Free demurrage days (after discharge) | Free detention days (after pickup) |
|---|---|---|
| US East Coast | 5 calendar days | 5 calendar days |
| US Gulf | 4 | 4 |
| US West Coast | 4 | 5 |
| EU North (DEHAM, NLRTM, BEANR) | 7 | 7 |
| UK (GBFXT, GBSOU) | 5 | 5 |
| AU (AUMEL, AUSYD, AUBNE) | 3 | 3 |
| Asia origins (variable) | 5–7 | 5–7 |

These are *typical*. Always cross-check the actual contract.

## Daily check protocol

Every business day at 09:00 local time, the ops associate reviews the demurrage exposure list. For each shipment with demurrage starting within 5 business days OR already accruing:

1. **Reconfirm the demurrage start date** by re-reading `demurrage_starts_at`.
2. **Verify the cargo is still in the terminal** (not yet picked up).
3. **Identify the blocker** — what's preventing pickup? (customs hold, doc issue, customer truck not booked)
4. **Estimate exposure for the next 5 business days** at the daily rate.
5. **Surface to the customer** if exposure exceeds tier-specific thresholds (see below).

## Customer disclosure thresholds

| Customer tier | Disclose to customer when total exposure exceeds |
|---|---|
| Platinum | $500 |
| Gold | $1,000 |
| Silver | $1,500 |
| Bronze | $2,000 |

Below threshold: we may absorb, write off, or include in routine billing. Above threshold: explicit customer comm required.

## Decision matrix — expedite vs negotiate

When demurrage is accruing, you have two levers:

| Lever | When to use | Expected outcome |
|---|---|---|
| **Expedite release** | Cargo blocker is solvable in <48h (e.g., customs doc just received) | Pay 1–2 days demurrage, release |
| **Negotiate waiver** | Blocker is carrier-side or terminal-side AND we have evidence | Carrier credits 50–100% on goodwill |
| **Negotiate amortization** | Customer is Gold+ AND blocker is shipper-side | Spread cost across next 3 invoices |
| **Re-route** | Blocker is at-port AND alternate port has capacity | Avoid further accrual; one-time cost |

## Carrier waiver request template

```
Subject: [Shipment ID] — Request for Demurrage Waiver Consideration

[Carrier Account Manager],

We're writing to request a goodwill demurrage waiver consideration for
[Shipment ID] / MBL [number].

Cargo discharged at [Port] on [date]. Demurrage accrual began on [date].
The blocker preventing release is [specific cause, ideally carrier-side
or terminal-side, e.g., "terminal congestion declared by Port Authority"].

Total exposure to date: $[amount] across [N] days.
Customer tier: [tier], relationship value: $[annual revenue if known].

We are requesting your consideration of a [50% / 100%] waiver in light
of [reason]. Happy to discuss alternatives.

Best regards,
[Operations Team]
```

**Hedge rules:**
- Never tell the customer "we will get it waived" before the carrier confirms.
- Always compute exposure conservatively (round up partial days).
- For carrier-side delays, document evidence in real time — claims after the fact rarely succeed.

## Common pitfalls

- **Pitfall 1:** Forgetting that weekends and holidays count for some carriers but not others. Read the contract.
- **Pitfall 2:** Pursuing a waiver from the local carrier office instead of the regional/global account. Local offices have no waiver authority.
- **Pitfall 3:** Disclosing demurrage to the customer too late. By the time exposure is $2,000+, the customer's tolerance for the news is gone.
