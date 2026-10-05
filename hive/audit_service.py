from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List


@dataclass(frozen=True)
class AuditEntry:
    timestamp: datetime
    actor: str
    action: str
    detail: str


class AuditService:
    def __init__(self) -> None:
        self._entries: List[AuditEntry] = []

    def log(self, actor: str, action: str, detail: str) -> AuditEntry:
        entry = AuditEntry(
            timestamp=datetime.now(timezone.utc),
            actor=actor,
            action=action,
            detail=detail,
        )
        self._entries.append(entry)
        return entry

    def entries(self) -> list[AuditEntry]:
        return list(self._entries)
