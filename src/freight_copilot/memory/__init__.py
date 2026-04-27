"""Long-term memory layer — SQLite-backed, multi-session.

Distinct from Phase 3's MemorySaver checkpointer (which holds in-process
message history per thread). This module gives every AgentSession access
to a shared db of notes, learned facts, and explicit corrections.
"""

from freight_copilot.memory.store import (
    Correction,
    CustomerNote,
    ShipmentNote,
    add_correction,
    add_customer_note,
    add_shipment_note,
    init_db,
    list_corrections,
    list_customer_notes,
    list_shipment_notes,
    now,
    reset_db,
)

__all__ = [
    "CustomerNote",
    "ShipmentNote",
    "Correction",
    "add_customer_note",
    "add_shipment_note",
    "add_correction",
    "list_customer_notes",
    "list_shipment_notes",
    "list_corrections",
    "init_db",
    "reset_db",
    "now",
]
