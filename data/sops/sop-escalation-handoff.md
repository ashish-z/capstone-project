# SOP-008 — Escalation Thresholds & Hand-off to Senior Ops

**Owner:** Operations · Quality
**Last reviewed:** 2026-03-05
**Applies to:** All exception cases. This SOP defines when a junior ops associate hands a case off to senior ops and what context must be passed.

---

## Why this SOP exists

A junior ops associate operates well within established playbooks. When a case exceeds a playbook's scope — financially, legally, or politically — escalation prevents:
- Costly mistakes (unauthorized commitments, missed customs deadlines)
- Customer relationship damage (Platinum customer not feeling heard at the right level)
- Carrier disputes (claims filed without proper documentation)

## Hard escalation triggers (always escalate)

If **any** of these are true, escalate immediately. Do not attempt to resolve.

1. **Cargo is at risk of customs seizure or forfeiture.**
2. **A High-severity HBL/MBL discrepancy** has been identified (different legal entities, cargo description mismatch). See **SOP-005**.
3. **Demurrage exposure exceeds $5,000** on any single shipment.
4. **A Platinum customer has explicitly asked to speak to "someone senior".**
5. **Carrier is refusing to honor a confirmed booking** (rare, but happens).
6. **Hazardous cargo (IMDG class 1, 6, or 7) is involved in the exception.**
7. **Force majeure has been declared** by the carrier.
8. **Legal letter, claim, or threat thereof** has been received.

## Soft escalation triggers (escalate if hour-threshold passes)

Tracked hourly. If still unresolved at the threshold, escalate.

| Trigger | Hours to escalation |
|---|---|
| Carrier silence on a Platinum shipment after our ping | 4 |
| Carrier silence on a Gold shipment after our ping | 8 |
| Customer hasn't acknowledged our incident comm (Platinum) | 4 |
| Customer hasn't acknowledged our incident comm (Gold) | 12 |
| Re-booking proposal pending customer approval (Gold+) | 12 |
| Demurrage clock runs in <48h with no resolution path | 0 (escalate now) |

## Hand-off package — what to send to senior ops

When you escalate, the senior ops engineer needs context fast. Send a single message (Slack, email, or TMS note) with:

```
ESCALATION — [Shipment ID]

Customer: [name] ([tier])
Carrier: [name]
Lane: [origin]–[destination]
Status: [current_status]
Days since exception detected: [N]

WHAT HAPPENED
[2–3 sentence summary]

WHAT I'VE TRIED
- [action] — [outcome]
- [action] — [outcome]

WHY ESCALATING
[Hard trigger #X / soft trigger that hit threshold]

CONSTRAINTS
- Customer SLA breach: [date and tier expectation]
- Demurrage starts: [date and rate]
- Vessel cutoff (if relevant): [date]

MY RECOMMENDATION
[What I would do if I had authority]

OPEN QUESTIONS
- [question 1]
- [question 2]

LINKS
- Shipment record: [TMS URL]
- Carrier email thread: [link]
- Customer email thread: [link]
```

A complete hand-off package lets the senior engineer act in <5 minutes.

## Common pitfalls

- **Pitfall 1:** Escalating without a recommendation. Senior ops has 50 escalations a week; "what would you do?" is a slower workflow than "I recommend X — agree?".
- **Pitfall 2:** Burying a hard trigger inside a long narrative. Lead with the trigger.
- **Pitfall 3:** Holding a case past the soft threshold because "I think I can fix it". The threshold exists for a reason; trust it.
- **Pitfall 4:** Not closing the loop. After senior ops resolves, update the customer comm log and the TMS notes, then mark the case closed.

## What "senior ops" means

In this organization, "senior ops" refers to:
- The on-call Senior Ops Engineer (rotational, 24×7 for Platinum tier, business hours otherwise)
- The Operations Manager during business hours
- The Director of Operations for hard-trigger #4 (Platinum executive escalation) or hard-trigger #8 (legal letter)

The escalation routing matrix in the TMS automatically picks the right tier based on the trigger.
