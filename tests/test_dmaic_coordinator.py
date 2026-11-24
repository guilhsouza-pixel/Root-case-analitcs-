from core.dmaic_coordinator import DMAICCoordinator
from core.dmaic_state import ProjectState
from core.evidence_registry import EvidenceItem, EvidenceRegistry


def tool_names(result):
    return [item.tool for item in result.tools]


def finding_codes(result):
    return {item.code for item in result.findings}


def test_evidence_is_hidden_until_allowed_phase():
    registry = EvidenceRegistry([
        EvidenceItem("D1", "Contexto inicial", "FATO", "DEFINE"),
        EvidenceItem("M1", "Baseline medido", "CÁLCULO", "MEASURE"),
        EvidenceItem("A1", "Validação técnica", "FATO", "ANALYZE"),
        EvidenceItem("I1", "Implementação", "FATO", "IMPROVE"),
        EvidenceItem("C1", "Resultado sustentado", "FATO", "CONTROL"),
    ])

    assert [x.id for x in registry.visible("DEFINE")] == ["D1"]
    assert [x.id for x in registry.visible("MEASURE")] == ["D1", "M1"]
    assert [x.id for x in registry.visible("ANALYZE")] == ["D1", "M1", "A1"]
    assert [x.id for x in registry.visible("CONTROL")] == ["D1", "M1", "A1", "I1", "C1"]


def test_megatech_full_dmaic_flow_preserves_chronology():
    state = ProjectState("Megatech")
    state.update_payload({
        "problem_statement": "Investigar oportunidade de melhorar a eficiência logística no fluxo Megatech–Anchieta.",
        "scope": "Acondicionamento e fluxo entre fornecedor e Anchieta.",
        "primary_indicator": "eficiência/custo logístico do fluxo",
        "primary_indicator_role": "Y",
        "team_roles": ["líder", "sponsor", "fornecedor", "transporte", "qualidade"],
        "multi_interface_process": True,
    }, "DEFINE")
    state.update_payload({
        "primary_indicator": "eficiência/custo logístico do fluxo",
        "primary_indicator_role": "Y",
        "measurement_definition": "baseline operacional definido a partir dos registros do fluxo",
        "data_source": "registros de embalagem e transporte",
        "baseline": "baseline medido",
        "needs_stratification": True,
    }, "MEASURE")
    state.update_payload({
        "analysis_question": "A oportunidade é tecnicamente viável sem impedimento de qualidade?",
        "analysis_type": "technical_validation",
        "evidence": "QA Peças validou a viabilidade técnica.",
        "forced_tool": False,
    }, "ANALYZE")
    state.update_payload({
        "selected_improvement": "Nova configuração de acondicionamento validada.",
        "implementation_evidence": "Fornecedor implementou a configuração aprovada.",
    }, "IMPROVE")
    state.update_payload({
        "control_indicator": "resultado logístico do fluxo",
        "owner": "Process Owner",
        "frequency": "semanal",
        "reaction_plan": "reavaliar o padrão se houver perda de desempenho ou impacto de qualidade.",
        "result_claimed": True,
        "sustainment_evidence": "resultado acompanhado após implantação.",
    }, "CONTROL")

    evidence = EvidenceRegistry([
        EvidenceItem("D1", "Fornecedor de alto volume e longa distância.", "FATO", "DEFINE"),
        EvidenceItem("D2", "Possibilidade de melhorar acondicionamento.", "HIPÓTESE", "DEFINE"),
        EvidenceItem("M1", "Quantidade/capacidade atual medida.", "CÁLCULO", "MEASURE"),
        EvidenceItem("A1", "QA Peças sem impedimento de qualidade.", "FATO", "ANALYZE"),
        EvidenceItem("I1", "Nova configuração implementada pelo fornecedor.", "FATO", "IMPROVE"),
        EvidenceItem("C1", "Resultado sustentado e acompanhado.", "FATO", "CONTROL"),
    ])
    coordinator = DMAICCoordinator(state, evidence)

    define = coordinator.evaluate()
    assert define.status == "READY"
    assert define.visible_evidence_ids == ["D1", "D2"]
    assert define.hidden_evidence_count == 4
    assert "project_charter" in tool_names(define)
    assert "sipoc" in tool_names(define)

    measure = coordinator.advance()
    assert state.phase == "MEASURE"
    assert measure.status == "READY"
    assert "M1" in measure.visible_evidence_ids
    assert "A1" not in measure.visible_evidence_ids

    analyze = coordinator.advance()
    assert state.phase == "ANALYZE"
    assert analyze.status == "READY"
    assert tool_names(analyze) == ["technical_validation"]
    assert "ishikawa" not in tool_names(analyze)
    assert "5_whys" not in tool_names(analyze)

    improve = coordinator.advance()
    assert state.phase == "IMPROVE"
    assert improve.status == "READY"

    control = coordinator.advance()
    assert state.phase == "CONTROL"
    assert control.status == "READY"
    assert control.next_phase is None
    assert "C1" in control.visible_evidence_ids


def test_bosch_define_advances_but_measure_blocks_unresolved_material_conflict():
    state = ProjectState("Bosch")
    state.update_payload({
        "problem_statement": "Indisponibilidade de embalagem no momento necessário.",
        "scope": "Circuito Bosch–VW–Kautex",
        "primary_indicator": "disponibilidade de embalagem",
        "primary_indicator_role": "Y",
        "team_roles": ["líder", "sponsor", "fornecedor", "logística"],
    }, "DEFINE")
    state.update_payload({
        "primary_indicator": "disponibilidade de embalagem",
        "primary_indicator_role": "Y",
        "measurement_definition": "percentual de necessidades atendidas com embalagem disponível",
        "data_source": "registros operacionais do circuito",
        "baseline": "a medir após reconciliação",
        "premise_conflicts": [{
            "topic": "float",
            "values": [7, 10],
            "resolved": False,
            "material": True,
        }],
    }, "MEASURE")

    coordinator = DMAICCoordinator(state)
    result = coordinator.advance()

    assert state.phase == "MEASURE"
    assert result.status == "BLOCKED"
    assert "UNRESOLVED_MATERIAL_PREMISE" in finding_codes(result)


def test_planmar_blocks_measure_when_inventory_is_not_primary_indicator_baseline():
    state = ProjectState("Planmar")
    state.update_payload({
        "problem_statement": "Risco de indisponibilidade de GLT1185 na preparação.",
        "scope": "Planmar e três plantas",
        "primary_indicator": "disponibilidade integral no início do preparo",
        "primary_indicator_role": "Y",
        "team_roles": ["planejamento", "logística", "fornecedor"],
    }, "DEFINE")
    state.update_payload({
        "primary_indicator": "disponibilidade integral no início do preparo",
        "primary_indicator_role": "Y",
        "measurement_definition": "percentual de preparações atendidas integralmente",
        "data_source": "inventário + EDI + eventos de retorno",
        "baseline": 425,
        "baseline_aligned_to_primary_indicator": False,
    }, "MEASURE")

    coordinator = DMAICCoordinator(state)
    result = coordinator.advance()

    assert result.status == "BLOCKED"
    assert "BASELINE_INDICATOR_MISMATCH" in finding_codes(result)


def test_pending_evidence_yields_ready_with_pending_not_blocked():
    state = ProjectState("Projeto com pendência")
    state.update_payload({
        "problem_statement": "Problema definido.",
        "scope": "Escopo definido.",
        "primary_indicator": "Indicador Y",
        "team_roles": ["líder", "sponsor"],
    })
    evidence = EvidenceRegistry([
        EvidenceItem("D1", "Contexto confirmado.", "FATO"),
        EvidenceItem("D2", "Responsável financeiro.", "A CONFIRMAR"),
    ])

    result = DMAICCoordinator(state, evidence).evaluate()

    assert result.status == "READY_WITH_PENDING"
    assert result.pending_evidence_ids == ["D2"]
    assert not result.blocked


def test_blocked_project_does_not_advance_phase():
    state = ProjectState("Bloqueado")
    state.update_payload({
        "problem_statement": "Problema",
        "scope": "Escopo",
        # indicador e equipe ausentes de propósito
    })
    coordinator = DMAICCoordinator(state)

    result = coordinator.advance()

    assert result.status == "BLOCKED"
    assert state.phase == "DEFINE"


def test_router_selects_measure_tools_only_when_requested_by_context():
    state = ProjectState("Measure routing", phase="MEASURE")
    state.update_payload({
        "primary_indicator": "tempo",
        "measurement_definition": "tempo por ciclo",
        "data_source": "cronômetro",
        "baseline": 10,
        "measurement_system_required": True,
        "measurement_system_checked": True,
        "needs_pareto": True,
        "needs_stratification": False,
    })
    result = DMAICCoordinator(state).evaluate()

    assert result.status == "READY"
    assert tool_names(result) == ["msa", "pareto"]


def test_control_completion_has_no_next_phase_and_records_completion():
    state = ProjectState("Projeto concluído", phase="CONTROL")
    state.update_payload({
        "control_indicator": "Y",
        "owner": "Process Owner",
        "frequency": "mensal",
        "reaction_plan": "reagir ao desvio",
        "result_claimed": True,
        "sustainment_evidence": "período estável",
    })
    coordinator = DMAICCoordinator(state)

    result = coordinator.advance()

    assert result.status == "READY"
    assert result.next_phase is None
    assert state.completed_phases == ["CONTROL"]

    coordinator.advance()
    assert state.completed_phases == ["CONTROL"]
    assert sum(item["event"] == "dmaic_completed" for item in state.history) == 1
