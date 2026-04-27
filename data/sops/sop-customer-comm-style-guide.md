# SOP-009 — Customer Communication Style Guide

**Owner:** Customer Success
**Last reviewed:** 2026-02-20
**Applies to:** Every customer-facing message drafted during exception handling. Pairs with **SOP-006 (tier comms)** which covers tier-specific tone.

---

## Five rules — every comm

### 1. Lead with impact, not cause

Customers care first about *what this means for them*, then about *why it happened*.

- ✅ "Your delivery promise of [date] is at risk by approximately 3 days."
- ❌ "MSC has rolled the booking to MSC BETA V.124N due to overbooking."

The cause comes in paragraph 2 or 3, after the impact is clear.

### 2. Hedge timelines, never commit on the carrier's behalf

| Don't write | Do write |
|---|---|
| "We will deliver by [date]" | "Carrier-revised ETA is [date], subject to [conditions]" |
| "It will be released today" | "We expect release within [X] business hours, pending [step]" |
| "The shipment is delayed by 3 days" | "ETA has slipped from [old] to [new], a delta of approximately 3 days" |

A specific date with no hedging is a contractual commitment in the customer's eyes.

### 3. Cite sources for every external-event claim

If you reference weather, port closure, strike, or any non-shipment-specific event: **cite the source**.

- ✅ "Per NOAA Storm Bulletin #14, Houston port is closed pending wind subsidence."
- ✅ "Per Unite the Union bulletin, work-to-rule action at Felixstowe was resolved on 26 April."
- ❌ "There's a storm in Houston so the port is closed."

This builds credibility and lets the customer verify independently.

### 4. Disclose financial exposure proactively

If demurrage, detention, or amendment fees may apply, surface them in the same comm where you describe the issue. Do not bury them in a follow-up.

- ✅ "Should the hold extend beyond [date], terminal demurrage of approximately $175/day will begin to accrue."
- ❌ (Demurrage discovered three weeks later in the final invoice)

### 5. Always end with a next step + cadence

Every customer comm closes with:
- The next concrete step (who is doing what)
- When the customer will hear from us again

- ✅ "We will provide an update within 4 hours, by 14:00 UTC."
- ❌ "We will keep you posted." (vague — sets no expectation)

## Forbidden phrases

These phrases damage trust or create legal exposure. Never use them in customer comms:

- "Trust me"
- "Don't worry"
- "I guarantee"
- "It's not our fault"
- "There's nothing we can do"
- "The carrier is being difficult"
- "Off the record" (the record is permanent)
- "Just between us"
- "I'll personally make sure" (we don't make personal commitments on company time)

## Required elements — every incident comm

| Element | Purpose |
|---|---|
| Shipment ID | Audit trail, customer reference |
| Carrier name | Customer can match to their visibility tools |
| MBL or HBL number | Required for any third-party verification |
| Current status (one phrase) | "Held at customs", "Rolled to V.124N", etc. |
| Cause (one sentence) | "Missing Commercial Invoice" |
| Source citation if external | "Per [source]" |
| Resolution path | "We are doing X" |
| Customer ask (if any) | "Please confirm Y" |
| Next-update commitment | "We will update by [time]" |
| Sign-off + return contact | Operations team alias + named exec for Gold+ |

If any of these are missing, the comm is incomplete.

## Email subject line format

```
[Shipment ID] — [One-line status]

Examples:
  FRT-1042 — Customs Hold Update & Expected Resolution Timeline
  FRT-1043 — Service Update: Tropical Storm Hermes
  FRT-1044 — Vessel Roll Notice
  FRT-1045 — Status Update Request
  FRT-1046 — Documentation Discrepancy Update
```

The customer's inbox should let them locate the comm by shipment ID at a glance.

## Tone calibration — the "forwarded to COO" test

Before sending any Gold or Platinum tier comm, ask:

> *If this email gets forwarded to the customer's COO without context, would I want my name on it?*

If the answer is no: revise tone, hedge more, cite more.

## Common pitfalls

- **Pitfall 1:** Apologizing reflexively for things outside our control. Acknowledge impact, but do not over-apologize for weather.
- **Pitfall 2:** Using internal jargon ("rolled", "MBL", "demurrage") without explaining. Customers understand "rolled" but not "the booking was off-loaded due to vessel slot reallocation".
- **Pitfall 3:** Sending a comm and then realizing a fact was wrong. Correct in writing, immediately, in a follow-up — do not delete or "rewrite history".
- **Pitfall 4:** Using a friendly Slack/Teams tone in formal email. Channel determines register.
