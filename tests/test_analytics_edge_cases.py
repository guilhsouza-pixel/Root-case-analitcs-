import math

import pandas as pd

from core.analytics import before_after, capability, control_limits, pareto_frame


def test_pareto_weighted_cost_uses_full_total():
    df = pd.DataFrame({
        "categoria": ["A", "A", "B", "C"],
        "custo": [10, 5, 3, 2],
    })
    out = pareto_frame(df, "categoria", "custo")
    assert list(out["valor"]) == [15, 3, 2]
    assert round(out.iloc[0]["percentual"], 6) == 75
    assert round(out.iloc[1]["acumulado"], 6) == 90
    assert round(out.iloc[-1]["acumulado"], 6) == 100


def test_capability_matches_reference_formula():
    series = pd.Series([8, 9, 10, 11, 12])
    cp, cpk = capability(series, 5, 15)
    expected_sigma = series.std(ddof=1)
    expected = (15 - 5) / (6 * expected_sigma)
    assert math.isclose(cp, expected, rel_tol=1e-12)
    assert math.isclose(cpk, expected, rel_tol=1e-12)


def test_capability_rejects_invalid_specification_limits():
    cp, cpk = capability(pd.Series([1, 2, 3]), 10, 5)
    assert cp is None
    assert cpk is None


def test_capability_rejects_zero_variation():
    cp, cpk = capability(pd.Series([5, 5, 5, 5]), 0, 10)
    assert cp is None
    assert cpk is None


def test_control_limits_reference_case():
    mean, ucl, lcl = control_limits(pd.Series([1, 2, 3]))
    assert mean == 2
    assert ucl == 5
    assert lcl == -1


def test_control_limits_empty_series_are_neutral():
    mean, ucl, lcl = control_limits(pd.Series(dtype=float))
    assert (mean, ucl, lcl) == (0.0, 0.0, 0.0)


def test_before_after_handles_zero_before_without_division_error():
    df = pd.DataFrame({
        "data": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-02-01", "2026-02-02"]),
        "custo": [0, 0, 5, 5],
    })
    result = before_after(df, "data", "custo", pd.Timestamp("2026-02-01"))
    assert result is not None
    assert result["media_antes"] == 0
    assert result["media_depois"] == 5
    assert result["reducao"] == 0
