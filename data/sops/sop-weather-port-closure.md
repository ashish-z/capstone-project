# SOP-002 — Weather-Induced Port Closure or ETA Slippage

**Owner:** Operations · Disruption Desk
**Last reviewed:** 2026-03-01
**Applies to:** Any shipment where the cause of delay is an external port event (storm, hurricane, port strike, terminal congestion declared by port authority) — not carrier-specific.

---

## When this SOP applies

- A shipment's ETA has slipped or its discharge port is closed.
- The carrier has identified the cause as external (weather, port authority, terminal fire).
- The cause is verifiable via at least one authoritative external source (NOAA, port authority bulletin, NHC, official news).

If the carrier blames "external" but no public-record confirmation exists, treat as **carrier-side** and use **SOP-007 — Carrier Schedule Disputes**.

## Diagnosis checklist

1. **Verify the event** with at least one independent authoritative source. Look up the destination port using the `external_events` tool.
2. **Get a carrier-issued revised ETA**, even a rough one. Do not invent one.
3. **Classify the event severity:**
   - **Class A (>72h closure or active hurricane warning):** Likely SLA breach for all tiers. Begin alternate-routing analysis.
   - **Class B (24–72h closure):** SLA breach for Platinum/Gold; manageable for Silver/Bronze.
   - **Class C (<24h closure):** No proactive action needed; monitor.

## Recommended actions

### Step 1 — Hold customer comm for the first 12 hours

External events are visible to the customer too. Sending a generic "your port is closed" within minutes adds noise without adding value. Wait for the carrier to issue a revised ETA, then send a single substantive comm.

**Exception:** Platinum and Gold tier customers expect to hear from us proactively within their SLA acknowledgment window regardless of whether we have the revised ETA. Send a holding comm citing the official source.

### Step 2 — Assess alternate routing

Use the `carrier_history` tool to identify alternate sailings on the same lane that bypass the affected port. For US East Coast, common alternates: ORF, BAL, SAV. For US Gulf: NOL, MOB. Only propose an alternate if the rate premium is <30% AND the alternate ETA improves SLA compliance.

### Step 3 — Update customer once carrier ETA is firm

Send the comm template below. Always **cite the external source** (e.g., "per NOAA Storm Bulletin") so the customer can verify independently.

## Customer communication template

```
Subject: [Shipment ID] — Service Update: [Event Name]

Dear [Consignee],

We are writing to inform you of a delay affecting shipment [Shipment ID].

[Origin Port] departure was on schedule. However, [Destination Port] is
currently closed due to [event type, e.g., "Tropical Storm Hermes"].
[Source: e.g., "NOAA Storm Bulletin #14"]

Current status: [vessel anchored offshore / awaiting berth slot / etc.]
Carrier-revised ETA: [date] [or "pending; expected within 24 hours"]

This is an external event outside our and the carrier's control. We are
monitoring the situation and will update you as soon as a firm berth
window is confirmed.

If you have time-sensitive cargo, please let us know — we can evaluate
alternate routing options.

Best regards,
[Operations Team]
```

**Hedge rules:**
- Always cite the source of the event (URL or bulletin number).
- Never write "we will deliver by [date]" — write "carrier-revised ETA is [date], subject to port reopening".
- Acknowledge customer impact without taking blame for an external event.

## Decision matrix — alternate routing

| Customer tier | Class A event | Class B event | Class C event |
|---|---|---|---|
| Platinum | Propose alternate within 4h | Propose alternate within 12h | Monitor |
| Gold | Propose alternate within 12h | Monitor unless SLA-critical | Monitor |
| Silver | Monitor unless customer asks | Monitor | Monitor |
| Bronze | Monitor | Monitor | Monitor |

## Common pitfalls

- **Pitfall 1:** Sending a customer comm before the carrier has issued a revised ETA — leads to follow-up confusion.
- **Pitfall 2:** Failing to attach a public-record source. Customers may distrust an "external event" claim without verification.
- **Pitfall 3:** Proposing alternate routing without checking lane economics. A 50% rate premium to save 1 day is rarely justifiable.
