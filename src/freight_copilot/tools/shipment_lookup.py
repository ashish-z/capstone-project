"""Shipment lookup tool — reads JSON fixtures from data/shipments/."""

from __future__ import annotations

import json
from pathlib import Path

from langchain_core.tools import tool

from freight_copilot.tools.models import ShipmentNotFound, ShipmentRecord

# Resolve relative to repo root so it works from any CWD.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_SHIPMENTS_DIR = _REPO_ROOT / "data" / "shipments"


@tool
def lookup_shipment(shipment_id: str) -> str:
    """Look up a shipment by its ID and return all known facts as JSON.

    Returns the full shipment record including tracking events, carrier notes,
    documents, and downstream constraints (SLA, demurrage, vessel cutoffs).

    Use this tool whenever the user mentions a shipment ID like 'FRT-1042'.
    The returned JSON is the ONLY source of truth for facts about the shipment;
    do not invent fields that aren't present.

    Args:
        shipment_id: The shipment identifier (e.g., 'FRT-1042').

    Returns:
        JSON string with the full shipment record, or an error message if not found.
    """
    fixture = _SHIPMENTS_DIR / f"{shipment_id}.json"
    if not fixture.exists():
        return ShipmentNotFound(
            shipment_id=shipment_id,
            message=(
                f"No shipment record found for '{shipment_id}'. "
                "Verify the ID with the user before proceeding."
            ),
        ).model_dump_json()

    raw = json.loads(fixture.read_text(encoding="utf-8"))
    # Validate at the tool boundary — a malformed fixture should fail loudly,
    # not silently propagate to the agent's reasoning.
    record = ShipmentRecord.model_validate(raw)
    return record.model_dump_json(exclude_none=False)
