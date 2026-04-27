"""Pydantic models for tool return shapes.

These exist so malformed fixtures fail loudly at the tool boundary rather
than silently producing wrong agent behavior. Each tool validates its own
return value against the matching model before handing it to the LLM.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _Permissive(BaseModel):
    """Allow extra fields — fixtures may carry optional / forward-compat keys
    we don't want to enforce yet."""

    model_config = ConfigDict(extra="allow")


# ---------------------------------------------------------------------------
# lookup_shipment
# ---------------------------------------------------------------------------


class TrackingEvent(_Permissive):
    ts: str
    event: str
    source: str | None = None


class CarrierNote(_Permissive):
    ts: str
    text: str
    source_from: str | None = Field(default=None, alias="from")


class PortRef(_Permissive):
    port_code: str
    port_name: str | None = None
    country: str | None = None


class CustomerRef(_Permissive):
    name: str
    tier: str | None = None
    sla_ack_hours: int | None = None


class DownstreamConstraints(_Permissive):
    customer_sla_breach_at: str | None = None
    vessel_cutoff_at: str | None = None
    demurrage_starts_at: str | None = None
    demurrage_rate_usd_per_day: float | int | None = None


class ShipmentRecord(_Permissive):
    """Schema the agent expects from lookup_shipment's success path."""

    shipment_id: str
    mode: str
    carrier: str
    current_status: str
    exception_summary: str | None = None
    origin: PortRef
    destination: PortRef
    customer: CustomerRef
    tracking_events: list[TrackingEvent] = Field(default_factory=list)
    carrier_notes: list[CarrierNote] = Field(default_factory=list)
    downstream_constraints: DownstreamConstraints | None = None


class ShipmentNotFound(BaseModel):
    error: str = "shipment_not_found"
    shipment_id: str
    message: str


# ---------------------------------------------------------------------------
# carrier_history
# ---------------------------------------------------------------------------


class LaneCarrierStat(_Permissive):
    carrier: str
    shipments: int
    on_time_pct: int
    avg_transit_days: int
    common_issues: list[str] = Field(default_factory=list)


class LaneHistory(_Permissive):
    lane: str
    carriers: list[LaneCarrierStat]


class LaneNotFound(BaseModel):
    error: str = "lane_not_found"
    lane: str
    message: str
    lanes_available: list[str]


# ---------------------------------------------------------------------------
# external_events
# ---------------------------------------------------------------------------


class ExternalEvent(_Permissive):
    type: str
    severity: str
    summary: str
    source: str
    start_date: str | None = None
    end_date_estimated: str | None = None
    source_url: str | None = None


class PortEvents(_Permissive):
    port_code: str
    port_name: str | None = None
    events: list[ExternalEvent]


class PortNotCovered(BaseModel):
    error: str = "port_not_covered"
    port_code: str
    message: str


def validate_or_raise(model: type[BaseModel], payload: Any) -> BaseModel:
    """Validate `payload` against `model`. Re-raises pydantic.ValidationError
    with a context message that points at the tool boundary."""
    return model.model_validate(payload)
