from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def _assert_no_exceptions(app):
    assert len(app.exception) == 0, [item.message for item in app.exception]


def test_coordinator_page_loads_and_blocks_empty_project():
    app = AppTest.from_file(APP_PATH, default_timeout=20).run()
    _assert_no_exceptions(app)

    # A navegação lateral deve conter a nova página.
    labels = [item.options for item in app.sidebar.radio]
    assert any("Coordenador DMAIC" in options for options in labels)

    nav = app.sidebar.radio[0]
    nav.set_value("Coordenador DMAIC")
    app.run()
    _assert_no_exceptions(app)

    assert any("Coordenador DMAIC" in item.value for item in app.header)

    # Projeto vazio deve ser bloqueado pelo gate, não quebrar a interface.
    evaluate_buttons = [button for button in app.button if button.label == "Avaliar gate"]
    assert evaluate_buttons, "Botão Avaliar gate não encontrado."
    evaluate_buttons[0].click()
    app.run()
    _assert_no_exceptions(app)

    assert any("Gate: Bloqueado" in item.value for item in app.subheader)


def test_coordinator_define_form_can_be_saved():
    app = AppTest.from_file(APP_PATH, default_timeout=20).run()
    app.sidebar.radio[0].set_value("Coordenador DMAIC")
    app.run()
    _assert_no_exceptions(app)

    # Preenche o mínimo do Define pela interface.
    areas = {item.label: item for item in app.text_area}
    inputs = {item.label: item for item in app.text_input}

    areas["Problema / oportunidade"].set_value("Investigar oportunidade logística no fluxo de um fornecedor.")
    areas["Escopo"].set_value("Fornecedor até planta.")
    inputs["Indicador primário (Y)"].set_value("Custo/eficiência logística do fluxo")
    inputs["Equipe / papéis principais"].set_value("líder, sponsor")

    save_buttons = [button for button in app.button if button.label == "Salvar dados da fase"]
    assert save_buttons, "Botão de salvar fase não encontrado."
    save_buttons[0].click()
    app.run()
    _assert_no_exceptions(app)

    # Após salvar, o gate deve poder ser avaliado sem bloqueios estruturais do Define.
    evaluate_buttons = [button for button in app.button if button.label == "Avaliar gate"]
    evaluate_buttons[0].click()
    app.run()
    _assert_no_exceptions(app)

    assert any(
        "Gate: Pronto" in item.value or "Gate: Pronto com pendências" in item.value
        for item in app.subheader
    )


def test_megatech_ui_keeps_measure_evidence_hidden_in_define():
    app = AppTest.from_file(APP_PATH, default_timeout=20).run()
    _assert_no_exceptions(app)

    app.sidebar.text_input[0].set_value("Megatech UI Validation")
    app.sidebar.radio[0].set_value("Coordenador DMAIC")
    app.run()
    _assert_no_exceptions(app)

    areas = {item.label: item for item in app.text_area}
    inputs = {item.label: item for item in app.text_input}

    areas["Problema / oportunidade"].set_value(
        "Investigar oportunidade de melhorar a eficiência logística no fluxo Megatech–Anchieta."
    )
    areas["Escopo"].set_value("Acondicionamento e fluxo entre fornecedor e Anchieta.")
    inputs["Indicador primário (Y)"].set_value("eficiência/custo logístico do fluxo")
    inputs["Equipe / papéis principais"].set_value(
        "líder, sponsor, fornecedor, transporte, qualidade"
    )

    [b for b in app.button if b.label == "Salvar dados da fase"][0].click()
    app.run()
    _assert_no_exceptions(app)

    # Evidência disponível já em Define.
    inputs = {item.label: item for item in app.text_input}
    areas = {item.label: item for item in app.text_area}
    selects = {item.label: item for item in app.selectbox}

    inputs["ID da evidência"].set_value("D1")
    areas["Descrição da evidência"].set_value(
        "Fornecedor de alto volume e localizado a longa distância da planta."
    )
    selects["Classificação"].set_value("FATO")
    selects["Liberar a partir da fase"].set_value("DEFINE")
    [b for b in app.button if b.label == "Adicionar / atualizar evidência"][0].click()
    app.run()
    _assert_no_exceptions(app)

    # Evidência conhecida hoje, mas que só poderia aparecer a partir de Measure.
    inputs = {item.label: item for item in app.text_input}
    areas = {item.label: item for item in app.text_area}
    selects = {item.label: item for item in app.selectbox}

    inputs["ID da evidência"].set_value("M1")
    areas["Descrição da evidência"].set_value("Quantidade/capacidade medida na fase Measure.")
    selects["Classificação"].set_value("CÁLCULO")
    selects["Liberar a partir da fase"].set_value("MEASURE")
    [b for b in app.button if b.label == "Adicionar / atualizar evidência"][0].click()
    app.run()
    _assert_no_exceptions(app)

    [b for b in app.button if b.label == "Avaliar gate"][0].click()
    app.run()
    _assert_no_exceptions(app)

    assert any("Gate: Pronto" in item.value for item in app.subheader)

    metrics = {item.label: str(item.value) for item in app.metric}
    assert metrics["Evidências liberadas"] == "1"
    assert metrics["Evidências futuras bloqueadas"] == "1"
    assert metrics["Pendências visíveis"] == "0"
