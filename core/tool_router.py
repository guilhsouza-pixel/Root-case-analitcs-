from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolDecision:
    tool: str
    reason: str


def select_tools(phase: str, payload: dict) -> list[ToolDecision]:
    phase = phase.upper().strip()
    decisions: list[ToolDecision] = []

    if phase == "DEFINE":
        decisions.append(ToolDecision("project_charter", "Estruturar problema, objetivo, escopo, governança e impacto."))
        if payload.get("multi_interface_process"):
            decisions.append(ToolDecision("sipoc", "Há múltiplas interfaces no processo; SIPOC ajuda a delimitar fornecedores, entradas, processo, saídas e clientes."))
        if payload.get("customer_requirements_needed"):
            decisions.append(ToolDecision("voc_ctq", "Há necessidade de traduzir requisitos do cliente em CTQs."))

    elif phase == "MEASURE":
        if payload.get("measurement_system_required"):
            decisions.append(ToolDecision("msa", "O indicador depende de um sistema de medição que precisa ser validado."))
        if payload.get("needs_stratification"):
            decisions.append(ToolDecision("stratification", "Os dados precisam ser segmentados para localizar concentração/variação."))
        if payload.get("needs_pareto"):
            decisions.append(ToolDecision("pareto", "É necessário priorizar categorias por frequência ou impacto."))

    elif phase == "ANALYZE":
        analysis_type = str(payload.get("analysis_type", "")).lower().strip()
        if analysis_type == "technical_validation":
            decisions.append(ToolDecision("technical_validation", "A pergunta é de viabilidade/restrição técnica; evidência especializada pode ser suficiente."))
        elif analysis_type == "hypothesis_test":
            decisions.append(ToolDecision("hypothesis_test", "A pergunta exige comparar grupos/efeitos com inferência estatística."))
        elif analysis_type == "regression":
            decisions.append(ToolDecision("regression", "A pergunta busca quantificar relação entre variáveis, sem presumir causalidade."))
        elif analysis_type == "cause_exploration":
            decisions.append(ToolDecision("cause_exploration", "Há necessidade de organizar causas potenciais antes da validação."))
        elif payload.get("analysis_question"):
            decisions.append(ToolDecision("evidence_review", "Há pergunta de análise definida; revisar evidências antes de escolher ferramenta adicional."))

    elif phase == "IMPROVE":
        if payload.get("multiple_alternatives"):
            decisions.append(ToolDecision("decision_matrix", "Há alternativas concorrentes que precisam ser priorizadas."))
        if payload.get("high_risk"):
            decisions.append(ToolDecision("risk_assessment", "A mudança é classificada como alto risco e requer avaliação antes da implementação."))
        if payload.get("pilot_required"):
            decisions.append(ToolDecision("pilot", "A solução precisa ser testada em escala controlada antes da implementação plena."))

    elif phase == "CONTROL":
        if payload.get("control_chart_claimed"):
            decisions.append(ToolDecision("control_chart", "O projeto pretende usar CEP para acompanhar estabilidade."))
        decisions.append(ToolDecision("control_plan", "A fase Control exige responsável, frequência, reação e sustentação do novo padrão."))

    return decisions
