from __future__ import annotations

from dataclasses import dataclass

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
    def __init__(self, state: ProjectState, evidence: EvidenceRegistry | None = None) -> None:
        self.state = state
        self.evidence = evidence or EvidenceRegistry()

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
        self.state.record(
            "gate_evaluated",
            status=status,
            next_phase=next_phase,
            blockers=[item.code for item in gate.blockers],
            tools=[item.tool for item in tools],
        )
        return result

    def advance(self) -> CoordinationResult:
        result = self.evaluate()
        if result.blocked:
            self.state.record("advance_blocked", blockers=[item.code for item in result.findings if item.severity == "BLOCKER"])
            return result

        if result.next_phase is None:
            self.state.record("dmaic_completed", status=result.status)
            return result

        self.state.move_to(result.next_phase)
        return self.evaluate()
