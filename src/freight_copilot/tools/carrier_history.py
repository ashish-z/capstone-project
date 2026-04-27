"""Carrier history tool — returns historical reliability/rate stats by lane."""

from __future__ import annotations

import json
from pathlib import Path

from langchain_core.tools import tool

_REPO_ROOT = Path(__file__).resolve().parents[3]
_LANE_HISTORY_FILE = _REPO_ROOT / "data" / "lane_history.json"


@tool
def carrier_history(lane: str) -> str:
    """Look up historical carrier performance on a specific lane (last 90 days).

    Use this tool when you need to compare carriers for a recommendation —
    e.g., "should we re-book on a different carrier?" or "what's our typical
    on-time performance with carrier X on this lane?".

    The lane string format is `{ORIGIN_PORT_CODE}-{DESTINATION_PORT_CODE}`,
    e.g., 'INNSA-USNYC' or 'VNSGN-DEHAM'. Port codes come from the shipment
    record's `origin.port_code` and `destination.port_code` fields.

    Returns JSON with per-carrier stats: shipments handled, on-time percentage,
    average transit days, average rate, and known recurring issues.

    Args:
        lane: Lane string in '{ORIGIN}-{DESTINATION}' format (e.g., 'INNSA-USNYC').

    Returns:
        JSON string with carrier performance data for that lane, or an error
        if the lane has no history on file.
    """
    payload = json.loads(_LANE_HISTORY_FILE.read_text(encoding="utf-8"))
    lane_data = payload["lanes"].get(lane)
    if lane_data is None:
        return json.dumps(
            {
                "error": "lane_not_found",
                "lane": lane,
                "message": (
                    f"No carrier history on file for lane '{lane}'. "
                    "Verify the port codes against the shipment record."
                ),
                "lanes_available": list(payload["lanes"].keys()),
            }
        )
    return json.dumps({"lane": lane, **lane_data})
