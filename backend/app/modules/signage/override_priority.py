"""Single source of truth for Screen Override priorities (UX-6C)."""

from __future__ import annotations

# Numeric bands — do not scatter magic numbers elsewhere.
OVERRIDE_PRIORITY: dict[str, int] = {
    "EMERGENCY": 400,
    "QUEUE_CALL": 300,
    "MANUAL": 200,
    "CAMPAIGN": 100,
}

# SCHEDULED_CONTENT / BASE is not a persisted override
BASE_PRIORITY = 0

OVERRIDE_TYPES = frozenset(OVERRIDE_PRIORITY.keys())
ADMIN_CREATABLE_TYPES = frozenset({"EMERGENCY", "MANUAL", "CAMPAIGN"})
TARGET_SCOPES = frozenset({"STORE", "QUEUE", "DISPLAY", "CHANNEL"})

QUEUE_CALL_DURATION_SECONDS = 7


def priority_for(override_type: str) -> int:
    key = (override_type or "").upper()
    if key not in OVERRIDE_PRIORITY:
        raise ValueError(f"override_type inválido: {override_type}")
    return OVERRIDE_PRIORITY[key]
