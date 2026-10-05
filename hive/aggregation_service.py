from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from hive.trust_service import ConfidentialityLevel, SubmissionContext, validate_submission


@dataclass(frozen=True)
class DeltaCandidate:
    device_id: str
    app_instance_id: str
    trust_score: float
    level: ConfidentialityLevel
    value: float

    def to_submission_context(self) -> SubmissionContext:
        return SubmissionContext(
            device_id=self.device_id,
            app_instance_id=self.app_instance_id,
            trust_score=self.trust_score,
            level=self.level,
        )


def weighted_average(candidates: Iterable[DeltaCandidate]) -> float:
    valid: list[DeltaCandidate] = []
    for candidate in candidates:
        submission = candidate.to_submission_context()
        ok, _ = validate_submission(submission)
        if ok and candidate.level in (ConfidentialityLevel.OFFEN, ConfidentialityLevel.VERTRAULICH):
            valid.append(candidate)

    if not valid:
        raise ValueError("no valid candidates available for aggregation")

    total_weight = sum(candidate.trust_score for candidate in valid)
    weighted_total = sum(candidate.value * candidate.trust_score for candidate in valid)
    return weighted_total / total_weight
