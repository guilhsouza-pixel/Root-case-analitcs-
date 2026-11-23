from core.database import Database
from core.dmaic_coordinator import DMAICCoordinator
from core.dmaic_state import ProjectState
from core.evidence_registry import EvidenceItem, EvidenceRegistry


def test_project_state_round_trip(tmp_path):
    db = Database(tmp_path / "dmaic.db")
    state = ProjectState("Projeto X")
    state.update_payload({
        "problem_statement": "Problema definido",
        "scope": "Escopo",
        "primary_indicator": "Y",
        "team_roles": ["líder"],
    })
    state.completed_phases = ["DEFINE"]
    state.phase = "MEASURE"

    db.save_project_state(state)
    loaded = db.load_project_state("Projeto X")

    assert loaded is not None
    assert loaded.project == "Projeto X"
    assert loaded.phase == "MEASURE"
    assert loaded.completed_phases == ["DEFINE"]
    assert loaded.phase_payloads["DEFINE"]["primary_indicator"] == "Y"


def test_evidence_registry_round_trip_and_snapshot_removes_stale(tmp_path):
    db = Database(tmp_path / "dmaic.db")
    first = EvidenceRegistry([
        EvidenceItem("E1", "Fato inicial", "FATO", "DEFINE", source="relato"),
        EvidenceItem("E2", "Resultado futuro", "CÁLCULO", "MEASURE", metadata={"valor": 10}),
    ])
    db.save_evidence_registry("Projeto X", first)

    loaded = db.load_evidence_registry("Projeto X")
    assert [x.id for x in loaded.all()] == ["E1", "E2"]
    assert loaded.all()[1].metadata["valor"] == 10

    second = EvidenceRegistry([
        EvidenceItem("E1", "Fato inicial revisado", "FATO", "DEFINE"),
    ])
    db.save_evidence_registry("Projeto X", second)

    loaded_again = db.load_evidence_registry("Projeto X")
    assert [x.id for x in loaded_again.all()] == ["E1"]
    assert loaded_again.all()[0].text == "Fato inicial revisado"


def test_coordinator_persists_phase_evidence_and_history(tmp_path):
    db = Database(tmp_path / "dmaic.db")
    state = ProjectState("Megatech persistida")
    state.update_payload({
        "problem_statement": "Investigar oportunidade logística.",
        "scope": "Fornecedor até planta",
        "primary_indicator": "Y logístico",
        "team_roles": ["líder", "sponsor"],
    }, "DEFINE")
    state.update_payload({
        "primary_indicator": "Y logístico",
        "measurement_definition": "definição operacional",
        "data_source": "fonte operacional",
        "baseline": "baseline medido",
    }, "MEASURE")

    evidence = EvidenceRegistry([
        EvidenceItem("D1", "Fato inicial", "FATO", "DEFINE"),
        EvidenceItem("M1", "Medição futura", "CÁLCULO", "MEASURE"),
    ])
    coordinator = DMAICCoordinator(state, evidence, store=db)

    result = coordinator.advance()

    assert result.phase == "MEASURE"
    assert state.phase == "MEASURE"

    loaded_state = db.load_project_state("Megatech persistida")
    loaded_evidence = db.load_evidence_registry("Megatech persistida")
    history = db.dataframe("dmaic_history", "Megatech persistida")

    assert loaded_state is not None
    assert loaded_state.phase == "MEASURE"
    assert [x.id for x in loaded_evidence.visible("DEFINE")] == ["D1"]
    assert [x.id for x in loaded_evidence.visible("MEASURE")] == ["D1", "M1"]
    assert "phase_changed" in set(history["event"])
    assert "gate_evaluated" in set(history["event"])


def test_new_coordinator_can_resume_persisted_project(tmp_path):
    db = Database(tmp_path / "dmaic.db")
    original = ProjectState("Retomada")
    original.update_payload({
        "problem_statement": "Problema",
        "scope": "Escopo",
        "primary_indicator": "Y",
        "team_roles": ["líder"],
    }, "DEFINE")
    original.update_payload({
        "primary_indicator": "Y",
        "measurement_definition": "medição",
        "data_source": "fonte",
        "baseline": 5,
    }, "MEASURE")
    registry = EvidenceRegistry([
        EvidenceItem("D1", "contexto", "FATO", "DEFINE"),
        EvidenceItem("M1", "baseline", "CÁLCULO", "MEASURE"),
    ])
    first = DMAICCoordinator(original, registry, store=db)
    first.advance()

    resumed_state = db.load_project_state("Retomada")
    resumed_registry = db.load_evidence_registry("Retomada")
    resumed = DMAICCoordinator(resumed_state, resumed_registry, store=db)
    result = resumed.evaluate()

    assert result.phase == "MEASURE"
    assert result.status == "READY"
    assert result.visible_evidence_ids == ["D1", "M1"]


def test_dataframe_supports_new_tables_without_id_column(tmp_path):
    db = Database(tmp_path / "dmaic.db")
    state = ProjectState("Projeto tabelas")
    db.save_project_state(state)
    db.save_evidence_registry(
        "Projeto tabelas",
        EvidenceRegistry([EvidenceItem("E1", "texto", "FATO")]),
    )

    projects = db.dataframe("dmaic_projects", "Projeto tabelas")
    evidence = db.dataframe("dmaic_evidence", "Projeto tabelas")

    assert len(projects) == 1
    assert len(evidence) == 1
