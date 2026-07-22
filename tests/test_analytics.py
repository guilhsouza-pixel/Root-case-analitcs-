import pandas as pd

from core.analytics import before_after, capability, pareto_frame
from core.schema import suggest_mapping


def test_pareto_orders_and_accumulates():
    df = pd.DataFrame({"categoria": ["A", "A", "B", "C"], "custo": [10, 5, 3, 2]})
    out = pareto_frame(df, "categoria", "contagem")
    assert out.iloc[0]["categoria"] == "A"
    assert round(out.iloc[-1]["acumulado"], 6) == 100


def test_capability_formula():
    series = pd.Series([8, 9, 10, 11, 12])
    cp, cpk = capability(series, 5, 15)
    assert cp is not None and cp > 1
    assert cpk is not None and cpk > 1


def test_before_after_reduction():
    df = pd.DataFrame({"data": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-02-01", "2026-02-02"]), "custo": [100, 100, 50, 50]})
    result = before_after(df, "data", "custo", pd.Timestamp("2026-02-01"))
    assert result is not None
    assert result["reducao"] == 50


def test_mapping_suggestions():
    mapping = suggest_mapping(["Data da ocorrência", "Fornecedor", "Custo total"])
    assert mapping["data"] == "Data da ocorrência"
    assert mapping["fornecedor"] == "Fornecedor"
    assert mapping["custo"] == "Custo total"

