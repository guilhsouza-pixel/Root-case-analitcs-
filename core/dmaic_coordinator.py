from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.dmaic_state import PHASES, ProjectState
from core.dmaic_validator import GateFinding, validate_phase
from core.evidence_registry import EvidenceRegistry
from core.tool_router import ToolDecision, select_tools


@dataclass
class CoordinationResult:
    project: str
    phase: str
    status: str
    next_phase: str | None
    findings: list[GateFinding]
    tools: list[ToolDecision]
    visible_evidence_ids: list[str]
    hidden_evidence_count: int
    pending_evidence_ids: list[str]

    @property
    def blocked(self) -> bool:
        return self.status == "BLOCKED"


class DMAICCoordinator:
    def __init__(
        self,
        state: ProjectState,
        evidence: EvidenceRegistry | None = None,
        store: Any | None = None,
    ) -> None:
        self.state = state
        self.evidence = evidence or EvidenceRegistry()
        self.store = store

    def _record(self, event: str, **details: Any) -> None:
        self.state.record(event, **details)
        if self.store is not None:
            self.store.append_coordinator_history(
                self.state.project,
                self.state.phase,
                event,
                details,
            )

    def _persist(self) -> None:
        if self.store is None:
            return
        self.store.save_project_state(self.state)
        self.store.save_evidence_registry(self.state.project, self.evidence)

    def evaluate(self) -> CoordinationResult:
        phase = self.state.phase
        payload = self.state.payload()
        payload["evidence_items"] = self.evidence.as_validator_payload(phase)

        gate = validate_phase(phase, payload)
        pending = self.evidence.pending(phase)
        tools = select_tools(phase, payload)

        if not gate.ready:
            status = "BLOCKED"
            next_phase = None
        else:
            status = "READY_WITH_PENDING" if pending else "READY"
            if phase == "CONTROL":
                next_phase = None
            else:
                next_phase = PHASES[PHASES.index(phase) + 1]

        result = CoordinationResult(
            project=self.state.project,
            phase=phase,
            status=status,
            next_phase=next_phase,
            findings=gate.findings,
            tools=tools,
            visible_evidence_ids=[item.id for item in self.evidence.visible(phase)],
            hidden_evidence_count=len(self.evidence.hidden(phase)),
            pending_evidence_ids=[item.id for item in pending],
        )
        self._record(
            "gate_evaluated",
            status=status,
            next_phase=next_phase,
            blockers=[item.code for item in gate.blockers],
            tools=[item.tool for item in tools],
        )
        self._persist()
        return result

    def advance(self) -> CoordinationResult:
        result = self.evaluate()
        if result.blocked:
            self._record(
                "advance_blocked",
                blockers=[
                    item.code
                    for item in result.findings
                    if item.severity == "BLOCKER"
                ],
            )
            self._persist()
            return result

        if result.next_phase is None:
            self._record("dmaic_completed", status=result.status)
            self._persist()
            return result

        previous_phase = self.state.phase
        self.state.move_to(result.next_phase)
        if self.store is not None:
            self.store.append_coordinator_history(
                self.state.project,
                self.state.phase,
                "phase_changed",
                {
                    "previous_phase": previous_phase,
                    "new_phase": self.state.phase,
                },
            )
        self._persist()
        return self.evaluate()
