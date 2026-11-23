from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

PHASE_ORDER = {
    "DEFINE": 1,
    "MEASURE": 2,
    "ANALYZE": 3,
    "IMPROVE": 4,
    "CONTROL": 5,
}

EVIDENCE_STATES = {"FATO", "CÁLCULO", "ESTIMATIVA", "HIPÓTESE", "RECOMENDAÇÃO", "A CONFIRMAR"}
BENEFIT_STATES = {"POTENCIAL", "ESTIMADO", "VALIDADO", "REALIZADO", "APROVADO FINANCEIRAMENTE"}


@dataclass
class GateFinding:
    code: str
    severity: str
    message: str


@dataclass
class GateResult:
    phase: str
    ready: bool
    findings: list[GateFinding] = field(default_factory=list)

    @property
    def blockers(self) -> list[GateFinding]:
        return [x for x in self.findings if x.severity == "BLOCKER"]


def _present(payload: dict, key: str) -> bool:
    value = payload.get(key)
    if isinstance(value, str):
        return bool(value.strip())
    return value is not None and value != [] and value != {}


def validate_evidence_labels(items: Iterable[dict]) -> list[GateFinding]:
    findings: list[GateFinding] = []
    for item in items:
        state = str(item.get("classification", "")).upper().strip()
        if state and state not in EVIDENCE_STATES:
            findings.append(GateFinding("INVALID_EVIDENCE_STATE", "BLOCKER", f"Classificação de evidência inválida: {state}."))
    return findings


def validate_benefit(benefit: dict) -> list[GateFinding]:
    findings: list[GateFinding] = []
    status = str(benefit.get("status", "")).upper().strip()
    if status and status not in BENEFIT_STATES:
        findings.append(GateFinding("INVALID_BENEFIT_STATUS", "BLOCKER", f"Status de benefício inválido: {status}."))
    if status in {"REALIZADO", "APROVADO FINANCEIRAMENTE"} and not benefit.get("evidence"):
        findings.append(GateFinding("FINANCIAL_EVIDENCE_REQUIRED", "BLOCKER", "Benefício realizado/aprovado exige evidência de realização ou validação financeira."))
    if benefit.get("type") in {"cost avoidance", "produtividade teórica", "benefício ambiental"} and benefit.get("direct_saving") is True:
        findings.append(GateFinding("FALSE_DIRECT_SAVING", "BLOCKER", "Cost avoidance, produtividade teórica ou benefício ambiental não podem ser classificados como saving direto."))
    return findings


def validate_cause(cause: dict) -> list[GateFinding]:
    findings: list[GateFinding] = []
    status = str(cause.get("status", "HIPÓTESE")).upper().strip()
    if status in {"VALIDADA", "CAUSA RAIZ", "CONFIRMADA"} and not cause.get("evidence"):
        findings.append(GateFinding("CAUSE_WITHOUT_EVIDENCE", "BLOCKER", "Uma causa não pode ser validada sem evidência observável ou mensurável."))
    return findings


def validate_phase(phase: str, payload: dict) -> GateResult:
    phase = phase.upper().strip()
    findings: list[GateFinding] = []

    if phase not in PHASE_ORDER:
        return GateResult(phase, False, [GateFinding("UNKNOWN_PHASE", "BLOCKER", "Fase DMAIC inválida.")])

    findings.extend(validate_evidence_labels(payload.get("evidence_items", [])))
    for benefit in payload.get("benefits", []):
        findings.extend(validate_benefit(benefit))
    for cause in payload.get("causes", []):
        findings.extend(validate_cause(cause))

    if phase == "DEFINE":
        for key, label in [
            ("problem_statement", "declaração do problema/oportunidade"),
            ("scope", "escopo"),
            ("primary_indicator", "indicador primário"),
            ("team_roles", "papéis principais"),
        ]:
            if not _present(payload, key):
                findings.append(GateFinding("DEFINE_MISSING_" + key.upper(), "BLOCKER", f"Define sem {label} suficiente."))

        if payload.get("uses_future_result"):
            findings.append(GateFinding("FUTURE_INFORMATION_LEAK", "BLOCKER", "O Define está usando resultado que só seria conhecido em fase posterior."))

        if payload.get("numeric_target") is not None and not _present(payload, "baseline"):
            findings.append(GateFinding("TARGET_WITHOUT_BASELINE", "BLOCKER", "Meta numérica não deve ser validada sem baseline medido ou fonte equivalente."))

        if payload.get("solution_committed") is True:
            findings.append(GateFinding("SOLUTION_IN_DEFINE", "BLOCKER", "A solução não deve ser tratada como definida dentro da declaração do problema."))

    elif phase == "MEASURE":
        for key, label in [
            ("primary_indicator", "indicador primário"),
            ("measurement_definition", "definição de medição"),
            ("data_source", "fonte de dados"),
            ("baseline", "baseline"),
        ]:
            if not _present(payload, key):
                findings.append(GateFinding("MEASURE_MISSING_" + key.upper(), "BLOCKER", f"Measure sem {label} suficiente."))

        if payload.get("measurement_system_required") and not payload.get("measurement_system_checked"):
            findings.append(GateFinding("MSA_PENDING", "BLOCKER", "O sistema de medição precisa ser verificado antes de usar os dados como baseline."))

    elif phase == "ANALYZE":
        if not _present(payload, "analysis_question"):
            findings.append(GateFinding("ANALYZE_NO_QUESTION", "BLOCKER", "Analyze precisa declarar a pergunta que está sendo testada."))
        if not _present(payload, "evidence"):
            findings.append(GateFinding("ANALYZE_NO_EVIDENCE", "BLOCKER", "Analyze precisa registrar evidência para sustentar a decisão."))
        if payload.get("forced_tool"):
            findings.append(GateFinding("FORCED_TOOL", "BLOCKER", "Ferramenta não deve ser obrigatória apenas por pertencer ao catálogo."))

    elif phase == "IMPROVE":
        if not _present(payload, "selected_improvement"):
            findings.append(GateFinding("IMPROVE_NO_SOLUTION", "BLOCKER", "Improve precisa registrar a melhoria selecionada."))
        if not _present(payload, "implementation_evidence"):
            findings.append(GateFinding("IMPROVE_NO_IMPLEMENTATION_EVIDENCE", "BLOCKER", "Implementação precisa de evidência de execução ou teste."))

    elif phase == "CONTROL":
        for key, label in [
            ("control_indicator", "indicador de controle"),
            ("owner", "responsável"),
            ("frequency", "frequência"),
            ("reaction_plan", "plano de reação"),
        ]:
            if not _present(payload, key):
                findings.append(GateFinding("CONTROL_MISSING_" + key.upper(), "BLOCKER", f"Control sem {label}."))
        if payload.get("result_claimed") and not _present(payload, "sustainment_evidence"):
            findings.append(GateFinding("CONTROL_NO_SUSTAINMENT", "BLOCKER", "Resultado sustentado exige evidência de acompanhamento após implementação."))

    return GateResult(phase, not any(x.severity == "BLOCKER" for x in findings), findings)
