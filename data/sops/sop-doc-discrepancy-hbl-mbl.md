# SOP-005 — Document Discrepancy: HBL/MBL Mismatch

**Owner:** Operations · Documentation Desk
**Last reviewed:** 2026-03-20
**Applies to:** Shipments where the destination agent or carrier has flagged a discrepancy between the House Bill of Lading (HBL) and the Master Bill of Lading (MBL), blocking cargo release.

---

## When this SOP applies

- Destination agent has refused to release cargo citing HBL/MBL mismatch.
- The discrepancy is in the **consignee** name/address, **shipper** name/address, or **cargo description** between the two BLs.
- Both BLs have been physically issued (i.e., past the point of pre-issuance correction).

If the discrepancy is detected *before* BL issuance, do not apply this SOP — issue a corrected draft instead.

## Severity classification

This is the most important diagnostic step. The correction path differs dramatically by severity.

| Severity | Examples | Correction path |
|---|---|---|
| **Low** | Entity-suffix mismatch (e.g., "ACME Inc." vs "ACME Inc Ltd."), trailing whitespace, capitalization | Letter of Indemnity (LOI) from consignee, signed and stamped |
| **Medium** | Address mismatch with same registered entity, or shipper-name mismatch where same company has multiple registered names | LOI + carrier amendment fee ($150–$400 typical) |
| **High** | Different legal entities entirely, cargo description mismatch (HS code, weight, description), origin/destination mismatch | Full BL amendment — **DO NOT** attempt LOI workaround |

For **High** severity, escalate to senior ops immediately and hand off to documentation team. **Never** attempt to resolve High-severity discrepancies inline — the legal and customs implications can be severe.

## Diagnosis checklist

1. **Pull both BLs** from the documents map. Verify the discrepancy is real (occasionally destination agents misread).
2. **Identify the discrepancy type** using the table above.
3. **Verify legal entity status** — for "ACME Inc." vs "ACME Inc Ltd." cases, confirm the registered company number is the same. If different, this is a **High** severity case, not a Low one.
4. **Check destination jurisdiction.** UK and EU destination agents are typically more flexible on Low-severity LOI; US East Coast is stricter.

## Recommended actions

### Step 1 — Confirm the diagnosis with the destination agent

Contact the destination agent in writing (not phone) requesting:
- Exact wording of the discrepancy
- Their accepted resolution path (LOI vs amendment)
- Their fee schedule for amendments

### Step 2 — Notify the customer (within tier SLA)

Use the comm template below. Be specific about severity and resolution path. Do **not** offer to resolve the discrepancy unilaterally.

### Step 3 — Coordinate the correction

For **Low** severity:
- Draft an LOI for customer signature
- Route through legal review if customer is Platinum tier
- Submit to destination agent

For **Medium/High** severity:
- Hand off to documentation team
- This SOP does not authorize you to proceed beyond customer notification

### Step 4 — Track demurrage exposure

The cargo cannot release until correction is complete. Calculate demurrage exposure starting from `downstream_constraints.demurrage_starts_at`.

## Customer communication template

```
Subject: [Shipment ID] — Documentation Discrepancy Update

Dear [Consignee],

Your shipment [Shipment ID] has arrived at [Destination Port] but cargo
release is currently blocked by the destination agent due to a
documentation discrepancy.

Specifically: the consignee name on the House Bill of Lading is recorded
as "[HBL value]", while the Master Bill of Lading shows "[MBL value]".
The destination agent has classified this as a [Low/Medium/High] severity
discrepancy.

Resolution path:
  [If Low]: A Letter of Indemnity from your team should resolve this.
  We will draft an LOI within the next [X hours] for your signature.
  Estimated time to release: 24–48 hours after LOI receipt.

  [If Medium]: A carrier-issued BL amendment is required. Estimated
  carrier fee: $[range]. Estimated time to release: 3–5 business days.

  [If High]: This requires escalation to our documentation team. We will
  contact you with a formal resolution proposal within [X hours].

Demurrage exposure begins on [date] at $[rate]/day. We will prioritize
resolution to minimize this.

Best regards,
[Operations Team]
```

**Hedge rules:**
- Never offer to "fix" the BL yourself. BLs are legal documents; corrections must go through the carrier.
- Never quote a release time without confirming with the destination agent first.
- For Medium/High severity, never proceed past the notification step without senior ops sign-off.

## Common pitfalls

- **Pitfall 1:** Misclassifying a High-severity discrepancy as Low to avoid escalation. This can lead to customs disputes and even cargo seizure.
- **Pitfall 2:** Drafting an LOI without confirming the destination agent will accept it. Always confirm acceptance criteria first.
- **Pitfall 3:** Forgetting that LOIs require the consignee's authorized signatory — a junior staff member's signature is often rejected.
