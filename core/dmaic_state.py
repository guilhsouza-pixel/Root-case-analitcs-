from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

PHASES = ("DEFINE", "MEASURE", "ANALYZE", "IMPROVE", "CONTROL")


@dataclass
class ProjectState:
    project: str
    phase: str = "DEFINE"
    phase_payloads: dict[str, dict[str, Any]] = field(default_factory=dict)
    completed_phases: list[str] = field(default_factory=list)
    history: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.phase = self.phase.upper().strip()
        if self.phase not in PHASES:
            raise ValueError(f"Fase DMAIC inválida: {self.phase}")
        for phase in PHASES:
            self.phase_payloads.setdefault(phase, {})

    def payload(self, phase: str | None = None) -> dict[str, Any]:
        target = (phase or self.phase).upper().strip()
        if target not in PHASES:
            raise ValueError(f"Fase DMAIC inválida: {target}")
        return dict(self.phase_payloads.get(target, {}))

    def update_payload(self, values: dict[str, Any], phase: str | None = None) -> None:
        target = (phase or self.phase).upper().strip()
        if target not in PHASES:
            raise ValueError(f"Fase DMAIC inválida: {target}")
        self.phase_payloads.setdefault(target, {}).update(values)

    def record(self, event: str, **details: Any) -> None:
        self.history.append({
            "event": event,
            "phase": self.phase,
            **details,
        })

    def move_to(self, phase: str) -> None:
        target = phase.upper().strip()
        if target not in PHASES:
            raise ValueError(f"Fase DMAIC inválida: {target}")
        if target != self.phase and self.phase not in self.completed_phases:
            self.completed_phases.append(self.phase)
        previous = self.phase
        self.phase = target
        self.record("phase_changed", previous_phase=previous, new_phase=target)
