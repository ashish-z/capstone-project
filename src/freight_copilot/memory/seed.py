"""Pre-seed the long-term memory db with realistic historical notes.

These notes simulate "the team has used this copilot for the last few
months" — past triages, customer-specific quirks, and corrections that
were made on previous sessions. They give the recall_* tools something
meaningful to return on day-one demos.

Run as:  PYTHONPATH=src python -m freight_copilot.memory.seed
"""

from __future__ import annotations

import time

from freight_copilot.memory.store import (
    Correction,
    CustomerNote,
    ShipmentNote,
    add_correction,
    add_customer_note,
    add_shipment_note,
    reset_db,
)

# Approximate timestamps for "this happened N days ago" — matches the
# 2026-04-27 conversation date of the rest of the project.
_DAY = 86400.0
_NOW = 1745700000.0  # ~ 2026-04-26 UTC


def seed_all() -> dict[str, int]:
    """Reset and re-populate the memory db. Idempotent."""
    reset_db()

    # ------------------------------------------------------------------
    # CUSTOMER NOTES — recurring patterns we've learned about each account
    # ------------------------------------------------------------------
    customer_notes = [
        # Brookline Apparel — Gold tier, on the customs-hold AT-1 fixture
        CustomerNote(
            ts=_NOW - 14 * _DAY,
            customer_name="Brookline Apparel Co",
            note=(
                "Shipper (Aurora Textiles Pvt Ltd) is historically slow on "
                "Commercial Invoice — typical 4–6h response time. Plan for "
                "this when promising customer ETAs on customs holds."
            ),
            source_thread_id="hist-2026-04-13",
        ),
        CustomerNote(
            ts=_NOW - 8 * _DAY,
            customer_name="Brookline Apparel Co",
            note=(
                "Customer's primary contact is procurement@brookline-apparel.com. "
                "They prefer 4-hour update cadence even within Gold's 4-hour SLA."
            ),
            source_thread_id="hist-2026-04-19",
        ),
        # Hanseatic Coffee — Gold tier, AT-3 rollover fixture
        CustomerNote(
            ts=_NOW - 21 * _DAY,
            customer_name="Hanseatic Coffee GmbH",
            note=(
                "Coffee is time-sensitive cargo. Customer cares most about "
                "narrow-window delivery; rate premium of ≤$300/container is "
                "typically acceptable for re-routes that protect the SLA."
            ),
            source_thread_id="hist-2026-04-06",
        ),
        # Lonestar — Silver tier, AT-2 weather fixture
        CustomerNote(
            ts=_NOW - 9 * _DAY,
            customer_name="Lonestar Manufacturing LLC",
            note=(
                "Customer has prior experience with Houston weather "
                "disruptions and tolerates them well. Single substantive "
                "comm with NOAA citation is preferred over multi-update "
                "cadence."
            ),
            source_thread_id="hist-2026-04-18",
        ),
        # Melbourne Tech — Platinum tier, AT-4 silent ETA fixture
        CustomerNote(
            ts=_NOW - 5 * _DAY,
            customer_name="Melbourne Tech Distributors",
            note=(
                "Platinum tier — executive sponsor (CFO) is on file. For any "
                "exception that risks SLA breach, copy regional-ops-apac@. "
                "They escalate quickly — proactively share AIS data when "
                "carrier portals are silent."
            ),
            source_thread_id="hist-2026-04-22",
        ),
        # ACME Inc — Silver tier, AT-5 doc discrepancy fixture
        CustomerNote(
            ts=_NOW - 30 * _DAY,
            customer_name="ACME Inc.",
            note=(
                "ACME has a parent entity 'ACME Inc Ltd.' (UK). HBL/MBL "
                "discrepancies between these are common and almost always "
                "low-severity entity-suffix mismatches, not legal-entity "
                "disputes. LOI is the standard path."
            ),
            source_thread_id="hist-2026-03-28",
        ),
    ]
    for n in customer_notes:
        add_customer_note(n)

    # ------------------------------------------------------------------
    # SHIPMENT NOTES — prior triages on these specific shipment IDs
    # ------------------------------------------------------------------
    shipment_notes = [
        ShipmentNote(
            ts=_NOW - 1 * _DAY,
            shipment_id="FRT-1042",
            note=(
                "Customs hold opened 2026-04-26. Shipper contact attempted at "
                "12:30 UTC — auto-reply received. Following up on next "
                "session. Demurrage starts 2026-04-30 at $175/day."
            ),
            source_thread_id="hist-2026-04-26",
        ),
        ShipmentNote(
            ts=_NOW - 2 * _DAY,
            shipment_id="FRT-1044",
            note=(
                "MSC ALPHA V.123N rolled to BETA V.124N. Original analysis "
                "favored Hapag-Lloyd alternate; customer approval pending. "
                "Vessel cutoff 2026-04-28 18:00 UTC."
            ),
            source_thread_id="hist-2026-04-25",
        ),
    ]
    for n in shipment_notes:
        add_shipment_note(n)

    # ------------------------------------------------------------------
    # CORRECTIONS — explicit fixes the user made on prior sessions
    # ------------------------------------------------------------------
    corrections = [
        Correction(
            ts=_NOW - 7 * _DAY,
            entity_kind="customer",
            entity_id="Brookline Apparel Co",
            correction=(
                "The customer's preferred contact for exception comms is "
                "procurement@brookline-apparel.com (NOT the generic info@). "
                "Use procurement@ for all incident emails."
            ),
            source_thread_id="hist-2026-04-20",
        ),
        Correction(
            ts=_NOW - 12 * _DAY,
            entity_kind="customer",
            entity_id="Lonestar Manufacturing LLC",
            correction=(
                "The shipper for Lonestar's Houston imports is in Ningbo "
                "(CNNGB), not Shenzhen (CNSZX) as the system master once "
                "showed. Always cross-check origin port from the shipment "
                "record, not from customer master."
            ),
            source_thread_id="hist-2026-04-15",
        ),
    ]
    for c in corrections:
        add_correction(c)

    return {
        "customer_notes": len(customer_notes),
        "shipment_notes": len(shipment_notes),
        "corrections": len(corrections),
    }


if __name__ == "__main__":
    import json

    stats = seed_all()
    print(json.dumps(stats, indent=2))
