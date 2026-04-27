# SOP-003 — Capacity Rollover (Vessel Roll)

**Owner:** Operations · Booking Desk
**Last reviewed:** 2026-03-10
**Applies to:** Any shipment where the carrier has rolled the booking from the originally confirmed vessel to a later sailing due to capacity constraints (overbooking).

---

## When this SOP applies

- Carrier has issued a roll notice on a confirmed booking.
- The cause is carrier-side capacity, not shipper readiness or documentation.
- The roll exceeds 24 hours.

If the cause is shipper-side (cargo not ready, late documentation), this is **not** a roll — it's a *no-show* and falls under **SOP-008 — No-Show Recovery**.

## Diagnosis checklist

1. **Confirm the new vessel and ETA** in writing from the carrier. Verify against the `lookup_shipment` record's `rolled_to_vessel`, `etd_after_roll`, `eta_after_roll` fields.
2. **Compute the SLA delta:** `eta_after_roll` minus `customer.delivery_promise_at` (if set) or `eta_original`.
3. **Check the alternate carrier landscape** with `carrier_history` for the same lane. Note which carriers have ETD windows before the rolled booking's new ETD.

## Recommended actions

### Step 1 — Acknowledge the customer within their tier SLA

Even before deciding on action, send a brief acknowledgment to the customer using the comm template below. Gold and Platinum tier customers expect this within 4 and 2 hours respectively.

### Step 2 — Decide: accept the roll, or re-book

**Re-book if any of these are true:**
- Customer is Platinum tier AND roll exceeds 48 hours.
- Customer is Gold tier AND roll causes SLA breach.
- An alternate carrier exists with on-time % >= 88 AND their ETD is before the rolled booking's new ETD AND the rate premium is <25%.

**Accept the roll if:**
- All three of the above conditions fail.
- Bill of Lading is already issued and re-papering would add >24h delay.
- Cargo is at-port and re-gating is not feasible before the alternate carrier's cutoff.

### Step 3 — If re-booking, secure customer pre-approval

**Never re-book without explicit customer approval** if the rate change is more than $200/container or any contract terms differ. Send the alternate-carrier proposal in writing, get a written yes, *then* execute.

### Step 4 — If accepting the roll, prepare a service-recovery proposal

For Gold/Platinum customers, a service-recovery gesture (rate reduction, priority handling on next booking, free document fee) often prevents escalation.

## Customer communication template (acknowledgment)

```
Subject: [Shipment ID] — Vessel Roll Notice

Dear [Consignee],

We have just been notified by [Carrier] that your shipment [Shipment ID]
has been rolled from [Original Vessel] to [New Vessel] due to vessel
overbooking on the [Origin]–[Destination] lane.

Revised dates:
  ETD: [old] → [new]
  ETA: [old] → [new]

Impact assessment: [The new ETA falls X days [before/after] your delivery
promise of Y / The new ETA still meets your delivery promise].

We are evaluating alternate carrier options on this lane that may restore
your original timeline. We will respond within [SLA window] with either:
  - A confirmation that the rolled booking is the best path, with a
    service-recovery proposal; or
  - An alternate-carrier proposal for your approval.

Best regards,
[Operations Team]
```

**Hedge rules:**
- Never describe an alternate as "booked" until the customer has approved AND the carrier has confirmed.
- Quote rate premiums explicitly when proposing an alternate.
- Do not share the reason ("overbooking") in a tone that blames the carrier — keep it factual.

## Decision matrix — re-book vs accept

| SLA delta | Customer tier | Action |
|---|---|---|
| Causes breach | Platinum | Re-book (any reasonable cost) |
| Causes breach | Gold | Re-book if alternate <25% premium |
| Causes breach | Silver | Re-book if alternate <10% premium; otherwise accept + service recovery |
| Causes breach | Bronze | Accept + service recovery |
| No breach | Any | Accept; routine notification |

## Common pitfalls

- **Pitfall 1:** Re-booking on price alone without checking the alternate's reliability. A cheap, unreliable carrier (<85% on-time) often produces a second roll.
- **Pitfall 2:** Forgetting to coordinate B/L re-issuance when re-booking. The original carrier's MBL must be voided and a new one issued.
- **Pitfall 3:** Quoting the alternate ETA from the alternate's published schedule rather than confirmed sailing — published schedules slip routinely.
