"""Hive trust and submission policy.

Coverage note: the validation flow is intentionally narrow and deterministic. We accept only a small set of
policy checks: non-empty identifiers, positive trust score, and rejection of local-only secrets. If future
business rules grow beyond that model, this module documentation must be updated in the same change.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class ConfidentialityLevel(IntEnum):
    OFFEN = 0
    VERTRAULICH = 1
    STRENG_GEHEIM = 2
    NUR_LOKAL = 3


@dataclass(frozen=True)
class SubmissionContext:
    device_id: str
    app_instance_id: str
    trust_score: float
    level: ConfidentialityLevel
    source: str = "device"

    def is_valid(self) -> bool:
        return bool(self.device_id) and bool(self.app_instance_id) and self.trust_score > 0.0

    def transport_allowed(self) -> bool:
        return self.level != ConfidentialityLevel.NUR_LOKAL and self.source != "network"


def validate_submission(context: SubmissionContext) -> tuple[bool, str]:
    if not context.device_id or not context.app_instance_id:
        return False, "missing device or app identifier"

    if context.trust_score <= 0:
        return False, "trust_score must be greater than zero"

    if context.level == ConfidentialityLevel.NUR_LOKAL:
        return False, "NUR_LOKAL submissions must remain local"

    return True, "accepted"
