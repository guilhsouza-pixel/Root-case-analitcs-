from core.dmaic_validator import validate_phase


def codes(result):
    return {f.code for f in result.findings}


def test_define_blocks_future_information_and_solution():
    result = validate_phase("DEFINE", {
        "problem_statement": "Oportunidade logística no fluxo do fornecedor.",
        "scope": "Fornecedor até planta",
        "primary_indicator": "custo logístico",
        "team_roles": ["líder", "sponsor"],
        "uses_future_result": True,
        "solution_committed": True,
    })
    assert not result.ready
    assert "FUTURE_INFORMATION_LEAK" in codes(result)
    assert "SOLUTION_IN_DEFINE" in codes(result)


def test_define_blocks_numeric_target_without_baseline():
    result = validate_phase("DEFINE", {
        "problem_statement": "Problema X",
        "scope": "Fluxo X",
        "primary_indicator": "Y",
        "team_roles": ["líder"],
        "numeric_target": 10,
    })
    assert not result.ready
    assert "TARGET_WITHOUT_BASELINE" in codes(result)


def test_analyze_accepts_lean_validation_without_ishikawa():
    result = validate_phase("ANALYZE", {
        "analysis_question": "A oportunidade é tecnicamente viável sem impacto de qualidade?",
        "evidence": "Validação técnica do QA",
        "causes": [],
        "forced_tool": False,
    })
    assert result.ready


def test_analyze_blocks_validated_cause_without_evidence():
    result = validate_phase("ANALYZE", {
        "analysis_question": "Qual hipótese explica o problema?",
        "evidence": "Dados do processo",
        "causes": [{"name": "falha do operador", "status": "VALIDADA"}],
    })
    assert not result.ready
    assert "CAUSE_WITHOUT_EVIDENCE" in codes(result)


def test_measure_requires_baseline_and_source():
    result = validate_phase("MEASURE", {
        "primary_indicator": "rotas/semana",
        "measurement_definition": "contagem de viagens planejadas",
    })
    assert not result.ready
    assert "MEASURE_MISSING_DATA_SOURCE" in codes(result)
    assert "MEASURE_MISSING_BASELINE" in codes(result)


def test_realized_saving_requires_evidence():
    result = validate_phase("CONTROL", {
        "control_indicator": "rotas/semana",
        "owner": "Transporte",
        "frequency": "semanal",
        "reaction_plan": "revisar programação",
        "sustainment_evidence": "4 semanas estáveis",
        "benefits": [{
            "type": "saving direto",
            "status": "REALIZADO",
            "value": 100000,
        }],
    })
    assert not result.ready
    assert "FINANCIAL_EVIDENCE_REQUIRED" in codes(result)


def test_control_blocks_claim_without_sustainment():
    result = validate_phase("CONTROL", {
        "control_indicator": "defeitos",
        "owner": "Qualidade",
        "frequency": "semanal",
        "reaction_plan": "conter e investigar",
        "result_claimed": True,
    })
    assert not result.ready
    assert "CONTROL_NO_SUSTAINMENT" in codes(result)


def test_cost_avoidance_not_direct_saving():
    result = validate_phase("CONTROL", {
        "control_indicator": "custo evitado",
        "owner": "Controller",
        "frequency": "mensal",
        "reaction_plan": "revalidar premissas",
        "benefits": [{
            "type": "cost avoidance",
            "status": "ESTIMADO",
            "direct_saving": True,
        }],
    })
    assert not result.ready
    assert "FALSE_DIRECT_SAVING" in codes(result)


def test_invalid_evidence_classification_is_blocked():
    result = validate_phase("DEFINE", {
        "problem_statement": "Problema",
        "scope": "Escopo",
        "primary_indicator": "Indicador Y",
        "team_roles": ["líder"],
        "evidence_items": [{"classification": "ACHISMO", "text": "não permitido"}],
    })
    assert not result.ready
    assert "INVALID_EVIDENCE_STATE" in codes(result)


def test_minor_premise_conflict_warns_but_does_not_block():
    result = validate_phase("DEFINE", {
        "problem_statement": "Problema",
        "scope": "Escopo",
        "primary_indicator": "Indicador Y",
        "team_roles": ["líder"],
        "premise_conflicts": [{
            "topic": "detalhe secundário",
            "resolved": False,
            "material": False,
        }],
    })
    assert result.ready
    assert "UNRESOLVED_MINOR_PREMISE" in codes(result)


def test_measure_blocks_required_msa_when_not_checked():
    result = validate_phase("MEASURE", {
        "primary_indicator": "dimensão medida",
        "measurement_definition": "medição dimensional",
        "data_source": "instrumento de medição",
        "baseline": 10.0,
        "measurement_system_required": True,
        "measurement_system_checked": False,
    })
    assert not result.ready
    assert "MSA_PENDING" in codes(result)


def test_analyze_blocks_forced_tool():
    result = validate_phase("ANALYZE", {
        "analysis_question": "A hipótese é suportada pelos dados?",
        "evidence": "dados disponíveis",
        "forced_tool": True,
    })
    assert not result.ready
    assert "FORCED_TOOL" in codes(result)


def test_improve_passes_when_required_pilot_and_risk_are_evidenced():
    result = validate_phase("IMPROVE", {
        "selected_improvement": "Alteração validada",
        "pilot_required": True,
        "pilot_evidence": "Piloto concluído com critérios atendidos",
        "high_risk": True,
        "risk_assessment": "Riscos avaliados e controles definidos",
        "implementation_evidence": "Mudança implementada",
    })
    assert result.ready


def test_control_passes_with_sustainment_and_financial_evidence():
    result = validate_phase("CONTROL", {
        "control_indicator": "custo logístico",
        "owner": "Process Owner",
        "frequency": "mensal",
        "reaction_plan": "acionar plano de reação se sair do limite",
        "result_claimed": True,
        "sustainment_evidence": "resultado estável no período de controle",
        "benefits": [{
            "type": "saving direto",
            "status": "APROVADO FINANCEIRAMENTE",
            "direct_saving": True,
            "evidence": "validação do controller",
        }],
    })
    assert result.ready


def test_unknown_phase_is_blocked():
    result = validate_phase("DESIGN", {})
    assert not result.ready
    assert "UNKNOWN_PHASE" in codes(result)
