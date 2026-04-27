# SOP-001 — Customs Hold: Missing Commercial Invoice

**Owner:** Operations · Customs Desk
**Last reviewed:** 2026-02-15
**Applies to:** US, EU, UK, AU import shipments where customs has flagged a hold pending receipt of the Commercial Invoice (CI).

---

## When this SOP applies

- A customs broker or destination agent has placed the shipment on hold.
- The reason given is "missing Commercial Invoice" or "incomplete commercial documentation".
- The shipment has cleared physical inspection (or inspection is not required).

If the hold reason is anything else (HS code dispute, valuation challenge, prohibited goods), use **SOP-006 — Customs Disputes** instead. Do not apply this SOP.

## Diagnosis checklist

1. **Confirm with the broker** that the only missing document is the CI. Brokers occasionally batch multiple issues into a single hold flag.
2. **Check the shipment's documents map** for `commercial_invoice` status. If marked `RECEIVED`, the issue is on the broker's side — escalate to the broker's manager, not the shipper.
3. **Note the time-to-demurrage clock.** Demurrage typically begins 5 business days after vessel discharge. Get the exact date from the shipment record's `downstream_constraints.demurrage_starts_at`.

## Recommended actions (in order)

### Step 1 — Contact the shipper (within 1 hour)

Email the shipper's documentation desk directly. Use the customer-tier comms SLA from **SOP-006**. Request:
- Commercial Invoice as PDF
- Confirmation it matches the values on the Packing List and Bill of Lading

**Do NOT** offer to provide the CI yourself or to "estimate" values. The CI must be issued by the shipper of record.

### Step 2 — Notify the consignee (within the SLA window)

Notify the consignee that a hold is in place and the cause. Use the customer comm template below. Be honest about the delay risk; do **not** promise a release time.

### Step 3 — Track demurrage exposure daily

If the CI is not received within 24 hours, calculate demurrage exposure for the next 5 business days and surface it to the customer in your follow-up.

### Step 4 — Escalate at thresholds

| Customer tier | Hand-off threshold |
|---|---|
| Platinum | If shipper unresponsive >2 hours |
| Gold | If shipper unresponsive >4 hours |
| Silver | If shipper unresponsive >24 hours |
| Bronze | If demurrage starts within 48 hours |

## Customer communication template

```
Subject: [Shipment ID] — Customs Hold Update

Dear [Consignee],

Your shipment [Shipment ID] arrived at [Port] on [Date] and was placed on
customs hold pending receipt of the Commercial Invoice from the shipper.
This is a documentation requirement, not a compliance issue.

We have contacted the shipper to request the document. We will provide
an update [within X hours / by end of day]. Should the hold extend
beyond [demurrage_starts_at], terminal demurrage charges of approximately
$[rate]/day will begin to accrue.

If you can assist in expediting the document from your supplier, please
let us know.

Best regards,
[Operations Team]
```

**Hedge rules:**
- Never write "we will release the shipment by [date]" — release is the broker's call.
- Never quote a customs duty figure unless it's confirmed by the broker.
- Always reference the demurrage start date from the shipment record, not memory.

## Common pitfalls

- **Pitfall 1:** Sending the customer a generic "we are working on it" comm with no specifics. The customer wants demurrage exposure and a follow-up time.
- **Pitfall 2:** Re-requesting the CI from the consignee. The consignee usually does not have it; the shipper does.
- **Pitfall 3:** Forgetting to reset the broker queue once the CI is received. After delivery, confirm the broker has acknowledged release.
