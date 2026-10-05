from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from hive.trust_service import ConfidentialityLevel


@dataclass(frozen=True)
class SlotInfo:
    slot_id: str
    category: str
    is_active: bool


class SlotRegistry:
    def __init__(self) -> None:
        self._slots: dict[str, SlotInfo] = {
            "legal": SlotInfo("legal", "Recht", True),
            "finance": SlotInfo("finance", "Finanzen", True),
            "medical": SlotInfo("medical", "Medizin", False),
            "engineering": SlotInfo("engineering", "Technik", True),
        }

    def resolve(self, requested: Iterable[str] | None) -> list[str]:
        if requested is None:
            return []

        resolved = []
        for slot_id in requested:
            normalized = slot_id.strip()
            if not normalized:
                continue
            slot = self._slots.get(normalized)
            if slot is None or not slot.is_active:
                continue
            resolved.append(normalized)

        return sorted(dict.fromkeys(resolved))

    def is_allowed_for_level(self, slot_id: str, level: ConfidentialityLevel) -> bool:
        slot = self._slots.get(slot_id)
        if slot is None or not slot.is_active:
            return False

        if level == ConfidentialityLevel.NUR_LOKAL:
            return False

        return True
