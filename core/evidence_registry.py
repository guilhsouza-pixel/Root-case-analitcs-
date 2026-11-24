from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from core.dmaic_state import PHASES

_PHASE_INDEX = {phase: index for index, phase in enumerate(PHASES)}


@dataclass(frozen=True)
class EvidenceItem:
    id: str
    text: str
    classification: str
    available_from_phase: str = "DEFINE"
    source: str | None = None
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        phase = self.available_from_phase.upper().strip()
        if phase not in _PHASE_INDEX:
            raise ValueError(f"Fase de liberação inválida: {self.available_from_phase}")
        object.__setattr__(self, "available_from_phase", phase)


class EvidenceRegistry:
    def __init__(self, items: Iterable[EvidenceItem] | None = None) -> None:
        self._items: list[EvidenceItem] = list(items or [])

    def add(self, item: EvidenceItem) -> None:
        if any(existing.id == item.id for existing in self._items):
            raise ValueError(f"Evidência duplicada: {item.id}")
        self._items.append(item)

    def upsert(self, item: EvidenceItem) -> None:
        self._items = [existing for existing in self._items if existing.id != item.id]
        self._items.append(item)

    def remove(self, evidence_id: str) -> None:
        self._items = [item for item in self._items if item.id != evidence_id]

    def all(self) -> list[EvidenceItem]:
        return list(self._items)

    def visible(self, phase: str) -> list[EvidenceItem]:
        phase = phase.upper().strip()
        if phase not in _PHASE_INDEX:
            raise ValueError(f"Fase DMAIC inválida: {phase}")
        threshold = _PHASE_INDEX[phase]
        return [
            item for item in self._items
            if _PHASE_INDEX[item.available_from_phase] <= threshold
        ]

    def hidden(self, phase: str) -> list[EvidenceItem]:
        visible_ids = {item.id for item in self.visible(phase)}
        return [item for item in self._items if item.id not in visible_ids]

    def as_validator_payload(self, phase: str) -> list[dict]:
        return [
            {
                "id": item.id,
                "text": item.text,
                "classification": item.classification,
                "source": item.source,
            }
            for item in self.visible(phase)
        ]

    def pending(self, phase: str) -> list[EvidenceItem]:
        return [
            item for item in self.visible(phase)
            if item.classification.upper().strip() == "A CONFIRMAR"
        ]
