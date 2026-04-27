"""External events tool — returns weather/port closures/strikes by port code."""

from __future__ import annotations

import json
from pathlib import Path

from langchain_core.tools import tool

_REPO_ROOT = Path(__file__).resolve().parents[3]
_EVENTS_FILE = _REPO_ROOT / "data" / "external_events.json"


@tool
def external_events(port_code: str) -> str:
    """Look up recent external events affecting a specific port.

    Use this tool when a shipment exception might be caused by a port-level
    event rather than a carrier or shipment issue — e.g., weather closures,
    labor strikes, or terminal congestion. Always check the destination port
    when ETA has slipped without an obvious carrier-side cause.

    Returns JSON with a list of events, each tagged by type, severity, date
    range, summary, and source. Empty list means no known events.

    Args:
        port_code: UN/LOCODE-style port code (e.g., 'USHOU' for Houston).

    Returns:
        JSON string with the port's known events, or an error if the port
        is not in our coverage.
    """
    payload = json.loads(_EVENTS_FILE.read_text(encoding="utf-8"))
    port_data = payload["ports"].get(port_code)
    if port_data is None:
        return json.dumps(
            {
                "error": "port_not_covered",
                "port_code": port_code,
                "message": (
                    f"No external-events feed configured for '{port_code}'. "
                    "Treat this as 'no signal' rather than 'no events'."
                ),
            }
        )
    return json.dumps({"port_code": port_code, **port_data})
