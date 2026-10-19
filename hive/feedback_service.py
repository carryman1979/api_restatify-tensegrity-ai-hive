from __future__ import annotations

from dataclasses import dataclass, field

from hive.trust_service import ConfidentialityLevel


@dataclass(frozen=True)
class EvidenceRef:
    source_id: str
    citation: str


@dataclass(frozen=True)
class FeedbackEvent:
    event_id: str
    app_instance_id: str
    model_id: str
    rating: int
    comment: str
    level: ConfidentialityLevel
    evidence: tuple[EvidenceRef, ...] = field(default_factory=tuple)


def validate_feedback(event: FeedbackEvent) -> tuple[bool, str]:
    if not event.event_id or not event.app_instance_id:
        return False, "missing event or app identifier"

    if event.rating not in (-1, 0, 1):
        return False, "rating must be -1, 0 or 1"

    if event.level == ConfidentialityLevel.NUR_LOKAL:
        return False, "NUR_LOKAL feedback must remain local"

    if event.rating != 0:
        if not event.evidence:
            return False, "rated feedback requires at least one evidence reference"
        for entry in event.evidence:
            if not entry.source_id or not entry.citation:
                return False, "evidence requires source and citation"

    return True, "accepted"
