"""Safety layer — output scanner + forbidden-pattern definitions.

The agent's hard rules live in the system prompt, but prompts are advisory.
This module is the durable, code-level safety net: it scans every agent
response for known unsafe patterns before showing it to the user.
"""

from freight_copilot.safety.scanner import SafetyFinding, SafetyReport, scan_response

__all__ = ["SafetyFinding", "SafetyReport", "scan_response"]
