"""Long-term memory recall tools — read from data/memory.sqlite3."""

from __future__ import annotations

import json
from dataclasses import asdict

from langchain_core.tools import tool

from freight_copilot.memory import (
    list_corrections,
    list_customer_notes,
    list_shipment_notes,
)


@tool
def recall_customer_history(customer_name: str, limit: int = 5) -> str:
    """Retrieve historical notes and corrections about a customer.

    Use this whenever the user mentions a customer by name (or you can
    derive the customer from a shipment record's `customer.name` field).
    Surfaces past triages, customer-specific quirks (preferred contacts,
    SLA expectations, recurring patterns), and corrections that the ops
    team made on prior sessions.

    The corrections are especially important — if a previous user told
    the agent "the customer is Platinum, not Gold", that correction is
    persisted here. Apply known corrections automatically.

    Args:
        customer_name: Exact customer name as it appears in the shipment
            record's `customer.name` field. Case-sensitive.
        limit: Max items to return per category (default 5).

    Returns:
        JSON string with two arrays: `notes` (historical observations)
        and `corrections` (explicit fixes from past sessions).
    """
    notes = list_customer_notes(customer_name, limit=limit)
    corrections = list_corrections("customer", customer_name, limit=limit)
    return json.dumps(
        {
            "customer_name": customer_name,
            "notes": [asdict(n) for n in notes],
            "corrections": [asdict(c) for c in corrections],
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
def recall_shipment_history(shipment_id: str, limit: int = 5) -> str:
    """Retrieve historical notes and corrections about a specific shipment.

    Use this when triaging a shipment to see whether we've worked it
    before — prior diagnoses, actions taken, follow-ups still pending,
    blockers we hit. This prevents duplicate work and surfaces context
    the current user may not know.

    Args:
        shipment_id: The shipment identifier (e.g., 'FRT-1042').
        limit: Max items to return per category (default 5).

    Returns:
        JSON string with `notes` and `corrections` arrays.
    """
    notes = list_shipment_notes(shipment_id, limit=limit)
    corrections = list_corrections("shipment", shipment_id, limit=limit)
    return json.dumps(
        {
            "shipment_id": shipment_id,
            "notes": [asdict(n) for n in notes],
            "corrections": [asdict(c) for c in corrections],
        },
        ensure_ascii=False,
        indent=2,
    )
