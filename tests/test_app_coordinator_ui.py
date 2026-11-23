from streamlit.testing.v1 import AppTest


def _assert_no_exceptions(app):
    assert len(app.exception) == 0, [item.message for item in app.exception]


def test_coordinator_page_loads_and_blocks_empty_project():
    app = AppTest.from_file("app.py", default_timeout=20).run()
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
    app = AppTest.from_file("app.py", default_timeout=20).run()
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
