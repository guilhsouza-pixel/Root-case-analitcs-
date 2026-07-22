from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def coerce_data(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    for col in ["data", "prazo"]:
        if col in result:
            result[col] = pd.to_datetime(result[col], errors="coerce", dayfirst=True)
    for col in ["quantidade", "tempo_parada", "custo", "gravidade", "frequencia"]:
        if col in result:
            if result[col].dtype == object:
                cleaned = result[col].astype(str).str.replace(r"[^0-9,.-]", "", regex=True)
                both = cleaned.str.contains(",", na=False) & cleaned.str.contains(r"\.", na=False)
                cleaned.loc[both] = cleaned.loc[both].str.replace(".", "", regex=False)
                cleaned = cleaned.str.replace(",", ".", regex=False)
                result[col] = pd.to_numeric(cleaned, errors="coerce")
            else:
                result[col] = pd.to_numeric(result[col], errors="coerce")
    return result


def pareto_frame(df: pd.DataFrame, category: str, metric: str = "contagem") -> pd.DataFrame:
    if category not in df or df.empty:
        return pd.DataFrame(columns=[category, "valor", "percentual", "acumulado"])
    base = df.dropna(subset=[category]).copy()
    if metric == "contagem":
        grouped = base.groupby(category, dropna=False).size().rename("valor")
    elif metric in base:
        grouped = base.groupby(category, dropna=False)[metric].sum(min_count=1).fillna(0).rename("valor")
    else:
        grouped = base.groupby(category, dropna=False).size().rename("valor")
    out = grouped.sort_values(ascending=False).reset_index()
    total = out["valor"].sum()
    out["percentual"] = np.where(total, out["valor"] / total * 100, 0)
    out["acumulado"] = out["percentual"].cumsum()
    return out


def pareto_chart(frame: pd.DataFrame, category: str, title: str) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    if frame.empty:
        fig.add_annotation(text="Sem dados para o Pareto", showarrow=False)
        return fig
    colors = ["#0B5CAB" if value <= 80 else "#9FB3C8" for value in frame["acumulado"]]
    fig.add_bar(x=frame[category].astype(str), y=frame["valor"], name="Impacto", marker_color=colors)
    fig.add_scatter(
        x=frame[category].astype(str), y=frame["acumulado"], name="% acumulado",
        mode="lines+markers", line=dict(color="#E4572E", width=3), secondary_y=True,
    )
    fig.add_hline(y=80, line_dash="dash", line_color="#E4572E", secondary_y=True)
    fig.update_yaxes(title_text="Impacto", secondary_y=False)
    fig.update_yaxes(title_text="Percentual acumulado", range=[0, 105], ticksuffix="%", secondary_y=True)
    fig.update_layout(title=title, hovermode="x unified", legend_orientation="h", margin=dict(t=70, b=30))
    return fig


def trend_frame(df: pd.DataFrame, frequency: str = "M") -> pd.DataFrame:
    if "data" not in df or df["data"].dropna().empty:
        return pd.DataFrame(columns=["periodo", "ocorrencias", "media_movel"])
    period = df.dropna(subset=["data"]).set_index("data").resample(frequency).size()
    out = period.rename("ocorrencias").reset_index().rename(columns={"data": "periodo"})
    out["media_movel"] = out["ocorrencias"].rolling(3, min_periods=1).mean()
    return out


def control_limits(series: pd.Series) -> tuple[float, float, float]:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return 0.0, 0.0, 0.0
    mean = float(clean.mean())
    std = float(clean.std(ddof=1)) if len(clean) > 1 else 0.0
    return mean, mean + 3 * std, mean - 3 * std


def capability(series: pd.Series, lsl: float, usl: float) -> tuple[float | None, float | None]:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if len(clean) < 2 or usl <= lsl:
        return None, None
    sigma = float(clean.std(ddof=1))
    if sigma == 0:
        return None, None
    mean = float(clean.mean())
    cp = (usl - lsl) / (6 * sigma)
    cpk = min((usl - mean) / (3 * sigma), (mean - lsl) / (3 * sigma))
    return cp, cpk


def automatic_insights(df: pd.DataFrame) -> list[dict[str, str]]:
    insights: list[dict[str, str]] = []
    if df.empty:
        return insights
    if "fornecedor" in df and df["fornecedor"].notna().any():
        share = df["fornecedor"].value_counts(normalize=True).head(3).sum() * 100
        leaders = ", ".join(df["fornecedor"].value_counts().head(3).index.astype(str))
        insights.append({"tipo": "Fato observado", "texto": f"Os 3 fornecedores mais recorrentes ({leaders}) concentram {share:.1f}% das ocorrências."})
    if "categoria" in df and df["categoria"].notna().any():
        counts = df["categoria"].value_counts()
        insights.append({"tipo": "Fato observado", "texto": f"A categoria mais frequente é “{counts.index[0]}”, com {counts.iloc[0]} ocorrência(s)."})
    if "tempo_parada" in df and df["tempo_parada"].notna().any() and "categoria" in df:
        total = df["tempo_parada"].sum()
        grouped = df.groupby("categoria")["tempo_parada"].sum().sort_values(ascending=False)
        if total > 0 and not grouped.empty:
            insights.append({"tipo": "Fato observado", "texto": f"“{grouped.index[0]}” responde por {grouped.iloc[0] / total * 100:.1f}% do tempo de parada registrado."})
    if "status" in df and "prazo" in df:
        open_mask = ~df["status"].astype(str).str.lower().isin(["concluido", "concluído", "cancelado"])
        overdue = open_mask & df["prazo"].notna() & (df["prazo"] < pd.Timestamp.today().normalize())
        if overdue.any():
            insights.append({"tipo": "Recomendação", "texto": f"Priorizar {int(overdue.sum())} ação(ões) vencida(s) e confirmar responsáveis e novo prazo."})
    insights.append({"tipo": "Evidência necessária", "texto": "Valide hipóteses de causa no processo antes de classificá-las como causa raiz."})
    return insights


def before_after(df: pd.DataFrame, date_col: str, metric: str, change_date: pd.Timestamp) -> dict[str, float] | None:
    if date_col not in df or metric not in df:
        return None
    clean = df[[date_col, metric]].dropna().copy()
    before = clean.loc[clean[date_col] < change_date, metric]
    after = clean.loc[clean[date_col] >= change_date, metric]
    if before.empty or after.empty:
        return None
    mean_before, mean_after = float(before.mean()), float(after.mean())
    reduction = ((mean_before - mean_after) / mean_before * 100) if mean_before else 0.0
    return {"media_antes": mean_before, "media_depois": mean_after, "diferenca": mean_before - mean_after, "reducao": reduction, "n_antes": len(before), "n_depois": len(after)}

