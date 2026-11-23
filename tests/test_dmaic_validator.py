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
