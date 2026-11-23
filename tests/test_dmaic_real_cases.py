from core.dmaic_validator import validate_phase


def codes(result):
    return {f.code for f in result.findings}


# TEST CASE 001 — MEGATECH
# Regra: reconstrução cronológica. Resultados futuros não entram no Define.
def test_megatech_define_accepts_only_initial_opportunity():
    result = validate_phase("DEFINE", {
        "problem_statement": "Investigar oportunidade de melhorar a eficiência logística no fluxo Megatech–Anchieta.",
        "scope": "Acondicionamento e fluxo dos revestimentos de coluna entre fornecedor e Anchieta.",
        "primary_indicator": "eficiência/custo logístico do fluxo",
        "primary_indicator_role": "Y",
        "team_roles": ["líder", "sponsor", "fornecedor", "transporte", "qualidade"],
        "uses_future_result": False,
        "solution_committed": False,
        "evidence_items": [
            {"classification": "FATO", "text": "Fornecedor de alto volume e longa distância."},
            {"classification": "HIPÓTESE", "text": "Pode existir oportunidade no acondicionamento."},
        ],
    })
    assert result.ready


def test_megatech_define_rejects_end_state_leak():
    result = validate_phase("DEFINE", {
        "problem_statement": "Reduzir rotas após aumento de múltiplo.",
        "scope": "Fluxo Megatech–Anchieta",
        "primary_indicator": "rotas/semana",
        "primary_indicator_role": "Y",
        "team_roles": ["líder", "sponsor"],
        "uses_future_result": True,
        "solution_committed": True,
        "baseline": 10,
        "numeric_target": 8,
    })
    assert not result.ready
    assert {"FUTURE_INFORMATION_LEAK", "SOLUTION_IN_DEFINE"} <= codes(result)


def test_megatech_analyze_accepts_quality_validation_as_sufficient_evidence():
    result = validate_phase("ANALYZE", {
        "analysis_question": "A oportunidade de aumento de acondicionamento é tecnicamente viável sem impedimento de qualidade?",
        "evidence": "QA Peças avaliou os requisitos e não identificou impedimento de qualidade.",
        "forced_tool": False,
        "causes": [],
    })
    assert result.ready


def test_megatech_improve_requires_implementation_evidence():
    blocked = validate_phase("IMPROVE", {
        "selected_improvement": "Nova configuração de acondicionamento validada tecnicamente.",
    })
    assert not blocked.ready
    assert "IMPROVE_NO_IMPLEMENTATION_EVIDENCE" in codes(blocked)

    ready = validate_phase("IMPROVE", {
        "selected_improvement": "Nova configuração de acondicionamento validada tecnicamente.",
        "implementation_evidence": "Fornecedor implementou fisicamente a nova configuração.",
    })
    assert ready.ready


# TEST CASE 002 — BOSCH
# Regra: premissas conflitantes permanecem A CONFIRMAR; o agente não escolhe uma arbitrariamente.
def test_bosch_blocks_material_float_conflict_when_used_for_measurement():
    result = validate_phase("MEASURE", {
        "primary_indicator": "disponibilidade de embalagem no momento da necessidade",
        "primary_indicator_role": "Y",
        "measurement_definition": "percentual de necessidades com embalagem disponível no ponto e horário requeridos",
        "data_source": "movimentos e registros operacionais do circuito",
        "baseline": "a medir",
        "premise_conflicts": [{
            "topic": "float",
            "values": [7, 10],
            "resolved": False,
            "material": True,
        }],
    })
    assert not result.ready
    assert "UNRESOLVED_MATERIAL_PREMISE" in codes(result)


def test_bosch_rejects_driver_as_primary_y():
    result = validate_phase("DEFINE", {
        "problem_statement": "Indisponibilidade de embalagem no fornecedor com risco de interrupção.",
        "scope": "Circuito Bosch–VW–Kautex",
        "primary_indicator": "lead time ponta a ponta",
        "primary_indicator_role": "driver",
        "team_roles": ["líder", "sponsor", "fornecedor", "logística"],
    })
    assert not result.ready
    assert "PRIMARY_INDICATOR_IS_DRIVER" in codes(result)


def test_bosch_estimated_benefit_can_remain_estimated_without_realization_claim():
    result = validate_phase("DEFINE", {
        "problem_statement": "Oportunidade de reduzir indisponibilidade e complexidade do fluxo.",
        "scope": "Circuito Bosch–VW–Kautex",
        "primary_indicator": "disponibilidade de embalagem",
        "primary_indicator_role": "Y",
        "team_roles": ["líder", "sponsor"],
        "benefits": [{
            "type": "saving direto",
            "status": "ESTIMADO",
            "value": 3000000,
            "direct_saving": True,
        }],
    })
    assert result.ready


# TEST CASE 003 — PLANMAR
# Regra: inventário total não é automaticamente baseline do indicador de disponibilidade no preparo.
def test_planmar_define_accepts_inventory_as_reference_not_baseline():
    result = validate_phase("DEFINE", {
        "problem_statement": "Risco de indisponibilidade de GLT1185 no momento de preparação das entregas.",
        "scope": "Planmar e fluxos para Anchieta, Taubaté e Curitiba.",
        "primary_indicator": "disponibilidade integral de GLT1185 no início planejado da preparação",
        "primary_indicator_role": "Y",
        "team_roles": ["planejamento", "operação logística", "fornecedor"],
        "evidence_items": [
            {"classification": "FATO", "text": "Inventário fotografado totaliza 425 GLT1185 em um corte específico."},
            {"classification": "A CONFIRMAR", "text": "Baseline do indicador de disponibilidade no preparo."},
        ],
    })
    assert result.ready


def test_planmar_measure_blocks_total_inventory_as_mismatched_baseline():
    result = validate_phase("MEASURE", {
        "primary_indicator": "disponibilidade integral de GLT1185 no início planejado da preparação",
        "primary_indicator_role": "Y",
        "measurement_definition": "percentual de preparações com quantidade integral de GLT1185 disponível no horário necessário",
        "data_source": "inventário, programação/EDI e eventos de retorno conciliados",
        "baseline": 425,
        "baseline_aligned_to_primary_indicator": False,
    })
    assert not result.ready
    assert "BASELINE_INDICATOR_MISMATCH" in codes(result)


# GOVERNANÇA E FINANCEIRO
def test_direct_savings_from_same_reduction_cannot_be_double_counted():
    result = validate_phase("CONTROL", {
        "control_indicator": "custo logístico",
        "owner": "Controller",
        "frequency": "mensal",
        "reaction_plan": "revalidar premissas e notas de crédito/faturas",
        "benefits": [
            {
                "type": "saving direto",
                "status": "VALIDADO",
                "direct_saving": True,
                "double_count_group": "mesma_reducao_de_rotas",
            },
            {
                "type": "saving direto",
                "status": "VALIDADO",
                "direct_saving": True,
                "double_count_group": "mesma_reducao_de_rotas",
            },
        ],
    })
    assert not result.ready
    assert "FINANCIAL_DOUBLE_COUNT" in codes(result)


def test_improve_high_risk_requires_risk_assessment_and_pilot_when_required():
    result = validate_phase("IMPROVE", {
        "selected_improvement": "Alteração operacional de alto impacto",
        "high_risk": True,
        "pilot_required": True,
        "implementation_evidence": "Plano de implementação preparado",
    })
    assert not result.ready
    assert "IMPROVE_RISK_ASSESSMENT_PENDING" in codes(result)
    assert "IMPROVE_PILOT_PENDING" in codes(result)
