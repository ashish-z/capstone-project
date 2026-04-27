# SOP-006 — Customer Tier Communication SLAs

**Owner:** Customer Success
**Last reviewed:** 2026-01-30
**Applies to:** All customer-facing communications during exception handling.

---

## Tier definitions

| Tier | Annual revenue | Account managed by | Examples in fixtures |
|---|---|---|---|
| **Platinum** | $500k+ | Named account exec + executive sponsor | Melbourne Tech Distributors |
| **Gold** | $100k–$500k | Named account exec | Brookline Apparel, Hanseatic Coffee |
| **Silver** | $20k–$100k | Pooled account team | Lonestar Manufacturing, ACME Inc. |
| **Bronze** | <$20k | Self-service / ops desk | (none in current fixtures) |

The customer tier is on every shipment record under `customer.tier`.

## Acknowledgment SLA windows

This is the time within which the customer expects to hear *something* from us once an exception is detected — even if the comm is just "we're aware and investigating".

| Tier | Acknowledgment SLA | Update cadence during incident | Resolution comm |
|---|---|---|---|
| Platinum | **2 hours** | Every 4 hours | Within 1 hour of resolution |
| Gold | **4 hours** | Every 8 hours | Within 2 hours of resolution |
| Silver | **8 hours** | Once per business day | Within 1 business day |
| Bronze | **24 hours** | When status changes | When closed |

The tier SLA is on the shipment record under `customer.sla_ack_hours`.

## Tone and content guidelines

### Platinum / Gold

- **Tone:** Formal, empathetic, executive-friendly. Assume the customer's COO may forward this email.
- **Content:** Lead with the impact ("your delivery promise of [date] is at risk"), then the cause, then your action plan.
- **Length:** Substantive — 4–8 short paragraphs. Brevity reads as dismissive at this tier.
- **Sign-off:** Named account exec, with backup contact.

### Silver

- **Tone:** Professional, friendly. Less ceremony than Gold.
- **Content:** Cause + status + next step. Skip the SLA framing unless they ask.
- **Length:** 3–5 paragraphs.
- **Sign-off:** Operations team alias OK.

### Bronze

- **Tone:** Direct, helpful.
- **Content:** What happened + what we're doing.
- **Length:** 2–4 paragraphs.
- **Sign-off:** Operations team alias.

## Universal rules — apply at every tier

### Hedging language

- ✅ "Currently estimated", "carrier-revised ETA", "subject to port reopening"
- ❌ "We will deliver by", "guaranteed", "confirmed"

A timeline becomes a commitment the moment it's stated without hedging language. We rarely have the authority to commit on the carrier's behalf.

### Source citation

For external events (weather, port closures, strikes): **always cite the source** (NOAA bulletin number, port authority bulletin, news outlet) so the customer can verify independently. This builds trust and protects us from "you made it up" pushback.

### Demurrage disclosure

When demurrage exposure exists, surface it explicitly:
- Calendar date when demurrage starts
- Daily rate
- Estimated total exposure if delay extends N more days

Customers who learn about demurrage in a final invoice escalate. Customers who learn about it in advance accept the risk.

### What never to say

| Don't say | Say instead |
|---|---|
| "It's the carrier's fault" | "The carrier has cited [reason]" |
| "There's nothing we can do" | "Within the constraints of [X], our options are [list]" |
| "I don't know" | "We are confirming this with [source] and will update by [time]" |
| "Trust me" | (cite a source or quantify) |
| "We guarantee" | "We currently estimate" |

## Comm channels

| Channel | When to use |
|---|---|
| Email | Default for all tiers and all incident comms |
| Phone | Platinum during Class A events; Gold if customer-initiated |
| Slack/Teams (if shared) | Active back-and-forth during a Platinum incident |
| TMS portal note | Always — even when also emailing — for audit trail |

## Common pitfalls

- **Pitfall 1:** Using a Gold-tier template tone for a Bronze customer (or vice versa). Tone mismatch reads as either patronizing or dismissive.
- **Pitfall 2:** Promising an update at "EOD" without specifying the timezone. EOD-PST and EOD-IST are 12 hours apart.
- **Pitfall 3:** Sending the same comm to consignee and shipper. They have different roles; they need different comms.
