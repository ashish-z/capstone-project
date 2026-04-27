"""Shared helpers used by every Streamlit page in this app.

Centralizes: sys.path setup so the freight_copilot package is importable,
custom CSS, and small UI primitives.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Streamlit invokes pages from app/, so the package needs to be on the path.
_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def fmt_ts(ts: float | None) -> str:
    """Render a unix epoch as 'YYYY-MM-DD HH:MM:SS UTC'."""
    if not ts:
        return "—"
    import datetime as _dt

    return _dt.datetime.fromtimestamp(ts, tz=_dt.timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )


def fmt_ms(ms: float | None) -> str:
    if ms is None:
        return "—"
    if ms < 1000:
        return f"{ms:.0f}ms"
    return f"{ms / 1000:.2f}s"


def fmt_usd(v: float | None) -> str:
    if v is None:
        return "—"
    return f"${v:.4f}" if v < 1 else f"${v:.2f}"


SAFETY_BADGE_COLORS = {
    "high": "🔴",
    "medium": "🟡",
    "low": "🟢",
}
