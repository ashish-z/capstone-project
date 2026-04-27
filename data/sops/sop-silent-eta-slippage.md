# SOP-004 — Silent ETA Slippage (Stale Tracking)

**Owner:** Operations · Tracking Desk
**Last reviewed:** 2026-02-25
**Applies to:** Shipments where the published ETA has passed (or will pass within 24 hours) AND the most recent carrier tracking event is older than 24 hours AND no carrier-issued delay notification has been received.

---

## When this SOP applies

- `eta` is in the past (or within 24h of now).
- Most recent `tracking_events` entry is >24h old.
- No `carrier_notes` entry from the carrier in the last 24h explaining the delay.
- Vessel is not in a known weather event area (verify with `external_events`).

If the carrier *has* notified us of a delay (even informally), this is not a "silent" slippage — use **SOP-002 (weather)** or **SOP-003 (rollover)** depending on the cause.

## Diagnosis checklist

1. **Cross-check vessel position via AIS** if the shipment record includes an `ais_external` event. If the vessel is within 24h of port at normal speed, the slippage is administrative (carrier hasn't published the arrival event).
2. **Check destination port for events** with the `external_events` tool — silent slippage during port congestion or labor action is common.
3. **Look for prior pattern:** does the carrier's `common_issues` list (from `carrier_history`) include "silent ETA slippage"? Some carriers (notably Evergreen on SGSIN-AUMEL) are systematic about this.

## Recommended actions

### Step 1 — Ping carrier ops desk (immediately)

Use the `carrier_contact.ops_email` and `carrier_contact.ops_phone` from the shipment record. Send a short query asking for current vessel status and ETA confirmation.

**Format:** "Hi [Carrier], requesting status update on [Shipment ID] / MBL [number]. Last published event was [date]. Customer is asking for current ETA. Thank you."

### Step 2 — Set a 4-hour escalation timer

If the carrier ops desk doesn't respond within 4 hours, escalate to `carrier_contact.escalation_email` (regional ops). Include the original ping + the elapsed silence.

### Step 3 — Prepare a customer holding comm

Don't send unless asked, but draft and queue. The customer may reach out before the carrier does — having a draft ready cuts response time from 30 minutes to 2 minutes.

### Step 4 — If still silent after 8 hours, escalate to senior ops

For Platinum/Gold customers, if no carrier response in 8 hours AND no AIS data is available, hand off to the senior ops team. Continued silence on a Gold+ shipment is itself an incident.

## Customer holding-comm template (draft, do not auto-send)

```
Subject: [Shipment ID] — Status Update Request

Dear [Consignee],

We are tracking shipment [Shipment ID] (vessel [name], voyage [number])
and noticed that the published tracking events are out of date relative
to your expected arrival on [eta].

We have contacted [Carrier]'s operations desk to request a current
status update and revised ETA. We will provide an update within
[X hours, default 4].

If you have specific delivery commitments dependent on this shipment,
please let us know and we will prioritize.

Best regards,
[Operations Team]
```

**Hedge rules:**
- Never write "your shipment is delayed by N days" — we don't yet know the magnitude.
- Never write "we have lost contact with the vessel" — alarming and usually inaccurate.
- Acknowledge our information gap honestly without overstating the issue.

## Escalation matrix

| Hours of carrier silence | Customer tier | Escalation step |
|---|---|---|
| 0–4 | Any | Send carrier ops desk ping |
| 4–8 | Platinum | Escalate to regional carrier ops + notify senior ops |
| 4–8 | Gold | Escalate to regional carrier ops |
| 4–8 | Silver/Bronze | Continue monitoring; second ping at hour 8 |
| 8–24 | Platinum | Senior ops hand-off; consider customer call |
| 8–24 | Gold | Senior ops hand-off |
| 24+ | Any | Treat as incident; trigger formal escalation process |

## Common pitfalls

- **Pitfall 1:** Assuming "no news is good news" on Evergreen and OOCL lanes. Silent slippage is a known pattern; do not wait passively.
- **Pitfall 2:** Pinging the carrier sales rep instead of the ops desk. Sales reps don't have visibility into operational ETA.
- **Pitfall 3:** Forgetting that AIS data is available externally — even when carrier portals are silent, vessel position is usually verifiable.
