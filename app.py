from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.analytics import (
    automatic_insights,
    before_after,
    capability,
    coerce_data,
    control_limits,
    pareto_chart,
    pareto_frame,
    trend_frame,
)
from core.database import Database
from core.report import build_pdf
from core.schema import CANONICAL_FIELDS, suggest_mapping


st.set_page_config(page_title="Root Cause Analytics", page_icon="🎯", layout="wide")

st.markdown(
    """
    <style>
    .block-container{padding-top:1.2rem;padding-bottom:3rem}.rca-hero{padding:1.1rem 1.3rem;border-radius:16px;
    background:linear-gradient(120deg,#082b4f,#0b5cab);color:#fff;margin-bottom:1rem}.rca-hero h1{margin:0;font-size:1.8rem}
    .rca-hero p{margin:.35rem 0 0;color:#d9e8f7}.insight{background:white;border-left:5px solid #0B5CAB;
    padding:.75rem 1rem;border-radius:8px;margin:.45rem 0;box-shadow:0 1px 4px #d7e0ea}.muted{color:#526273;font-size:.9rem}
    [data-testid="stMetric"]{background:#fff;border:1px solid #dbe4ee;padding:12px;border-radius:12px}
    </style>
    <div class="rca-hero"><h1>ROOT CAUSE ANALYTICS</h1><p>Lean Six Sigma • análise orientada por evidências</p></div>
    """,
    unsafe_allow_html=True,
)

DB_PATH = Path(__file__).with_name("root_cause_analytics.db")
db = Database(DB_PATH)


def load_uploaded(uploaded, sheet_name=None) -> pd.DataFrame:
    name = uploaded.name.lower()
    raw = uploaded.getvalue()
    if name.endswith(".csv"):
        for encoding in ("utf-8-sig", "latin-1"):
            try:
                return pd.read_csv(BytesIO(raw), sep=None, engine="python", encoding=encoding)
            except UnicodeDecodeError:
                continue
        raise ValueError("Não foi possível identificar a codificação do CSV.")
    return pd.read_excel(BytesIO(raw), sheet_name=sheet_name or 0)


def excel_sheets(uploaded) -> list[str]:
    if uploaded.name.lower().endswith((".xls", ".xlsx")):
        return pd.ExcelFile(BytesIO(uploaded.getvalue())).sheet_names
    return []


def mapped_frame(raw: pd.DataFrame, mapping: dict[str, str | None]) -> pd.DataFrame:
    selected = {source: target for target, source in mapping.items() if source and source in raw.columns}
    out = raw[list(selected)].rename(columns=selected).copy() if selected else raw.copy()
    return coerce_data(out)


def format_brl(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def data_required() -> pd.DataFrame | None:
    frame = st.session_state.get("data")
    if frame is None or frame.empty:
        st.info("Importe e mapeie uma planilha na página **Importação** para liberar esta análise.")
        return None
    return frame


def apply_filters(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    result = df.copy()
    labels: list[str] = []
    with st.sidebar.expander("Filtros globais", expanded=True):
        if "data" in result and result["data"].notna().any():
            low, high = result["data"].min().date(), result["data"].max().date()
            chosen = st.date_input("Período", value=(low, high), min_value=low, max_value=high)
            if isinstance(chosen, tuple) and len(chosen) == 2:
                start, end = pd.Timestamp(chosen[0]), pd.Timestamp(chosen[1]) + pd.Timedelta(days=1)
                result = result[(result["data"] >= start) & (result["data"] < end)]
                labels.append(f"{chosen[0]:%d/%m/%Y}–{chosen[1]:%d/%m/%Y}")
        for col in ["fornecedor", "transportadora", "planta", "area", "processo", "categoria", "produto", "embalagem", "responsavel", "status", "gravidade"]:
            if col in result and result[col].notna().any():
                options = sorted(result[col].dropna().astype(str).unique().tolist())
                selected = st.multiselect(CANONICAL_FIELDS.get(col, col.title()), options, key=f"filter_{col}")
                if selected:
                    result = result[result[col].astype(str).isin(selected)]
                    labels.append(f"{CANONICAL_FIELDS.get(col, col)}: {', '.join(selected)}")
    return result, labels


def render_import() -> None:
    st.header("Importação e mapeamento")
    st.caption("O sistema preserva o arquivo original e cria uma camada padronizada para as análises.")
    uploaded = st.file_uploader("Selecione Excel ou CSV", type=["xls", "xlsx", "csv"])
    if not uploaded:
        st.markdown("Importe sua planilha para iniciar. Os dados permanecem na sessão do aplicativo e não são incorporados ao código.")
        return
    sheets = excel_sheets(uploaded)
    sheet = st.selectbox("Aba", sheets) if sheets else None
    try:
        raw = load_uploaded(uploaded, sheet)
    except Exception as exc:
        st.error(f"Não foi possível ler o arquivo: {exc}")
        return
    st.success(f"Arquivo lido: {len(raw):,} linhas × {len(raw.columns)} colunas".replace(",", "."))
    st.dataframe(raw.head(50), use_container_width=True)

    suggestions = suggest_mapping(raw.columns.tolist())
    saved = db.load_mappings()
    preset_name = st.selectbox("Mapeamento salvo", ["Detecção automática", *saved.keys()])
    preset = suggestions if preset_name == "Detecção automática" else saved[preset_name]
    options = ["— Não mapear —", *map(str, raw.columns)]
    st.subheader("Correspondência das colunas")
    mapping: dict[str, str | None] = {}
    cols = st.columns(3)
    for idx, (field, label) in enumerate(CANONICAL_FIELDS.items()):
        suggested = preset.get(field)
        default = options.index(suggested) if suggested in options else 0
        chosen = cols[idx % 3].selectbox(label, options, index=default, key=f"map_{field}")
        mapping[field] = None if chosen == options[0] else chosen
    left, right = st.columns([2, 1])
    map_name = left.text_input("Nome para salvar este mapeamento", placeholder="Ex.: RDL Anchieta")
    if right.button("Salvar mapeamento", use_container_width=True, disabled=not map_name):
        db.save_mapping(map_name.strip(), mapping)
        st.success("Mapeamento salvo.")
    if st.button("Aplicar e analisar", type="primary", use_container_width=True):
        if not any(mapping.values()):
            st.error("Mapeie pelo menos uma coluna.")
        else:
            st.session_state.data = mapped_frame(raw, mapping)
            st.session_state.source_name = uploaded.name
            st.success("Dados preparados. Abra a Visão executiva no menu.")


def render_overview(df: pd.DataFrame) -> None:
    st.header("Visão executiva")
    total = len(df)
    cost = float(df["custo"].sum()) if "custo" in df else 0.0
    downtime = float(df["tempo_parada"].sum()) if "tempo_parada" in df else 0.0
    recurrence = int(df.duplicated(subset=[c for c in ["categoria", "fornecedor", "processo"] if c in df], keep=False).sum()) if any(c in df for c in ["categoria", "fornecedor", "processo"]) else 0
    completed = df["status"].astype(str).str.lower().isin(["concluido", "concluído"]).mean() * 100 if "status" in df else 0
    overdue = 0.0
    if "prazo" in df and "status" in df:
        open_mask = ~df["status"].astype(str).str.lower().isin(["concluido", "concluído", "cancelado"])
        overdue = (open_mask & (df["prazo"] < pd.Timestamp.today().normalize())).mean() * 100
    cards = st.columns(6)
    values = [("Ocorrências", f"{total}"), ("Reincidências", f"{recurrence}"), ("Tempo de parada", f"{downtime:,.1f}"), ("Custo total", format_brl(cost)), ("Ações concluídas", f"{completed:.1f}%"), ("Ações vencidas", f"{overdue:.1f}%")]
    for col, (label, value) in zip(cards, values):
        col.metric(label, value)
    c1, c2 = st.columns([1.7, 1])
    dimension = next((c for c in ["categoria", "fornecedor", "processo"] if c in df), None)
    if dimension:
        c1.plotly_chart(pareto_chart(pareto_frame(df, dimension), dimension, f"Pareto — {CANONICAL_FIELDS[dimension]}"), use_container_width=True)
    trend = trend_frame(df, "MS")
    if not trend.empty:
        fig = px.line(trend, x="periodo", y=["ocorrencias", "media_movel"], markers=True, title="Tendência e média móvel")
        c2.plotly_chart(fig, use_container_width=True)
    st.subheader("Insights automáticos")
    for item in automatic_insights(df):
        st.markdown(f"<div class='insight'><b>{item['tipo']}</b><br>{item['texto']}</div>", unsafe_allow_html=True)


def render_occurrences(df: pd.DataFrame) -> None:
    st.header("Análise de ocorrências")
    numeric = [c for c in ["quantidade", "tempo_parada", "custo", "gravidade", "frequencia"] if c in df]
    categorical = [c for c in ["categoria", "fornecedor", "processo", "produto", "embalagem", "causa", "status"] if c in df]
    if categorical:
        dimension = st.selectbox("Dimensão", categorical, format_func=lambda x: CANONICAL_FIELDS[x])
        metric = st.selectbox("Métrica", ["contagem", *numeric], format_func=lambda x: "Quantidade de registros" if x == "contagem" else CANONICAL_FIELDS[x])
        top = pareto_frame(df, dimension, metric).head(30)
        st.plotly_chart(px.bar(top, x=dimension, y="valor", color="percentual", color_continuous_scale="Blues", title="Ranking"), use_container_width=True)
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_pareto(df: pd.DataFrame) -> None:
    st.header("Pareto 80/20")
    categories = [c for c in ["categoria", "fornecedor", "processo", "produto", "embalagem", "causa", "status"] if c in df]
    metrics = ["contagem", *[c for c in ["quantidade", "tempo_parada", "custo"] if c in df]]
    if not categories:
        st.warning("Mapeie ao menos uma dimensão categórica.")
        return
    c1, c2 = st.columns(2)
    category = c1.selectbox("Analisar por", categories, format_func=lambda x: CANONICAL_FIELDS[x])
    metric = c2.selectbox("Medir por", metrics, format_func=lambda x: "Quantidade de ocorrências" if x == "contagem" else CANONICAL_FIELDS[x])
    frame = pareto_frame(df, category, metric)
    st.plotly_chart(pareto_chart(frame, category, "Causas vitais e causas triviais"), use_container_width=True)
    vital = frame[frame["acumulado"].shift(fill_value=0) < 80]
    st.info(f"{len(vital)} item(ns) formam o grupo prioritário e acumulam {vital['percentual'].sum():.1f}% do impacto.")
    st.dataframe(frame, use_container_width=True, hide_index=True)


def render_stratification(df: pd.DataFrame) -> None:
    st.header("Estratificação")
    dims = [c for c in ["fornecedor", "categoria", "processo", "produto", "embalagem", "gravidade", "frequencia", "status"] if c in df]
    if len(dims) < 2:
        st.warning("Mapeie ao menos duas dimensões para realizar o cruzamento.")
        return
    a, b = st.columns(2)
    row = a.selectbox("Linhas", dims, format_func=lambda x: CANONICAL_FIELDS[x])
    col = b.selectbox("Colunas", [x for x in dims if x != row], format_func=lambda x: CANONICAL_FIELDS[x])
    pivot = pd.crosstab(df[row].fillna("Não informado"), df[col].fillna("Não informado"))
    tab1, tab2, tab3 = st.tabs(["Heatmap", "Barras empilhadas", "Tabela"])
    tab1.plotly_chart(px.imshow(pivot, text_auto=True, aspect="auto", color_continuous_scale="Blues"), use_container_width=True)
    long = pivot.reset_index().melt(id_vars=row, var_name=col, value_name="ocorrencias")
    tab2.plotly_chart(px.bar(long, x=row, y="ocorrencias", color=col, barmode="stack"), use_container_width=True)
    tab3.dataframe(pivot, use_container_width=True)


def render_trends(df: pd.DataFrame) -> None:
    st.header("Tendências")
    if "data" not in df or df["data"].dropna().empty:
        st.warning("Mapeie uma coluna de data.")
        return
    freq = st.segmented_control("Granularidade", options=["Dia", "Semana", "Mês"], default="Mês")
    code = {"Dia": "D", "Semana": "W-MON", "Mês": "MS"}[freq]
    trend = trend_frame(df, code)
    fig = go.Figure()
    fig.add_scatter(x=trend["periodo"], y=trend["ocorrencias"], mode="lines+markers", name="Ocorrências")
    fig.add_scatter(x=trend["periodo"], y=trend["media_movel"], mode="lines", name="Média móvel", line=dict(dash="dash"))
    fig.update_layout(title="Evolução no tempo", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
    if len(trend) >= 2:
        last, previous = trend["ocorrencias"].iloc[-1], trend["ocorrencias"].iloc[-2]
        change = ((last - previous) / previous * 100) if previous else 0
        st.info(f"O último período apresentou variação de {change:+.1f}% em relação ao anterior. A tendência não prova causalidade.")


def render_capability(df: pd.DataFrame) -> None:
    st.header("Estatística e capabilidade")
    numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if not numeric:
        st.warning("Não há variável numérica mapeada.")
        return
    metric = st.selectbox("Variável", numeric, format_func=lambda x: CANONICAL_FIELDS.get(x, x))
    clean = df[metric].dropna()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Média", f"{clean.mean():.2f}")
    c2.metric("Mediana", f"{clean.median():.2f}")
    c3.metric("Desvio-padrão", f"{clean.std():.2f}")
    c4.metric("Amplitude", f"{clean.max() - clean.min():.2f}")
    a, b = st.columns(2)
    a.plotly_chart(px.histogram(df, x=metric, marginal="box", title="Distribuição"), use_container_width=True)
    mean, ucl, lcl = control_limits(clean)
    chart = go.Figure(go.Scatter(x=np.arange(1, len(clean) + 1), y=clean, mode="lines+markers", name=metric))
    chart.add_hline(y=mean, line_color="#0B5CAB", annotation_text="Média")
    chart.add_hline(y=ucl, line_dash="dash", line_color="#C62828", annotation_text="LSC")
    chart.add_hline(y=lcl, line_dash="dash", line_color="#C62828", annotation_text="LIC")
    chart.update_layout(title="Carta de controle exploratória")
    b.plotly_chart(chart, use_container_width=True)
    st.caption("Os limites de controle são estimados pelos dados e não substituem limites de especificação.")
    st.subheader("Cp e Cpk")
    x, y = st.columns(2)
    lsl = x.number_input("Limite inferior de especificação", value=float(clean.min()))
    usl = y.number_input("Limite superior de especificação", value=float(clean.max()))
    cp, cpk = capability(clean, lsl, usl)
    if cp is None:
        st.warning("Dados ou limites insuficientes para calcular Cp e Cpk.")
    else:
        x.metric("Cp", f"{cp:.3f}")
        y.metric("Cpk", f"{cpk:.3f}")


ISHIKAWA_CATEGORIES = ["Mão de obra", "Método", "Máquina", "Material", "Medição", "Meio ambiente"]


def render_ishikawa(project: str) -> None:
    st.header("Ishikawa — 6M")
    with st.form("ishikawa_form", clear_on_submit=True):
        problem = st.text_input("Problema central")
        c1, c2, c3 = st.columns(3)
        category = c1.selectbox("Categoria 6M", ISHIKAWA_CATEGORIES)
        cause = c2.text_input("Causa potencial")
        subcause = c3.text_input("Subcausa")
        c4, c5, c6 = st.columns(3)
        status = c4.selectbox("Situação", ["Hipótese", "Validada", "Descartada"])
        owner = c5.text_input("Responsável pela validação")
        evidence = c6.text_input("Evidência")
        save = st.form_submit_button("Adicionar causa", type="primary")
        if save and problem and cause:
            db.execute("INSERT INTO ishikawa(project,problem,category,cause,subcause,status,evidence,owner) VALUES(?,?,?,?,?,?,?,?)", (project, problem, category, cause, subcause, status, evidence, owner))
            st.success("Causa registrada.")
    frame = db.dataframe("ishikawa", project)
    if frame.empty:
        st.info("Cadastre causas potenciais para construir o diagrama.")
        return
    problem = st.selectbox("Problema visualizado", frame["problem"].unique())
    view = frame[frame["problem"] == problem]
    colors = {"Hipótese": "#F9A825", "Validada": "#2E7D32", "Descartada": "#78909C"}
    fig = go.Figure()
    positions = {name: (0 if i < 3 else 2, 2 - (i % 3)) for i, name in enumerate(ISHIKAWA_CATEGORIES)}
    for category_name, (x, y) in positions.items():
        subset = view[view["category"] == category_name]
        label = category_name + ("<br>" + "<br>".join("• " + c[:32] for c in subset["cause"].astype(str).head(5)) if not subset.empty else "")
        fig.add_annotation(x=x, y=y, text=label, showarrow=True, ax=120 if x == 0 else -120, ay=0, bgcolor="#E8EEF6", bordercolor="#0B5CAB")
    fig.add_annotation(x=1, y=1, text=f"<b>EFEITO</b><br>{problem[:60]}", showarrow=False, bgcolor="#0B5CAB", font=dict(color="white"), borderpad=12)
    fig.update_xaxes(visible=False, range=[-0.3, 2.3]); fig.update_yaxes(visible=False, range=[-0.6, 2.6]); fig.update_layout(height=520, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(view[["category", "cause", "subcause", "status", "evidence", "owner"]], use_container_width=True, hide_index=True,
                 column_config={"status": st.column_config.TextColumn("Situação")})
    st.caption("Uma hipótese só deve ser marcada como validada quando houver evidência observável ou mensurável.")


def render_five_whys(project: str) -> None:
    st.header("5 Porquês")
    levels = st.number_input("Número de níveis", 3, 10, 5)
    with st.form("why_form", clear_on_submit=True):
        problem = st.text_area("Descrição objetiva do problema")
        whys = [st.text_input(f"Por quê {i + 1}") for i in range(int(levels))]
        root = st.text_input("Causa raiz encontrada")
        a, b = st.columns(2)
        evidence = a.text_area("Evidências")
        validation = b.text_area("Método de validação")
        c, d, e = st.columns(3)
        action = c.text_input("Ação corretiva")
        owner = d.text_input("Responsável")
        due = e.date_input("Prazo")
        status = st.selectbox("Status", ["Não iniciado", "Em andamento", "Validado", "Concluído"])
        if st.form_submit_button("Salvar análise", type="primary") and problem:
            chain = json.dumps([w for w in whys if w], ensure_ascii=False)
            db.execute("INSERT INTO why5(project,problem,chain,root_cause,evidence,validation,action,owner,due_date,status) VALUES(?,?,?,?,?,?,?,?,?,?)", (project, problem, chain, root, evidence, validation, action, owner, str(due), status))
            st.success("Análise salva.")
            text = " ".join([root, action]).lower()
            if "operador" in text and not evidence:
                st.warning("A análise atribui a causa ao operador sem evidência. Investigue também método, padrão, treinamento, condição e sistema.")
            if action and "treinamento" in action.lower():
                st.warning("Treinamento isolado raramente elimina uma causa sistêmica. Considere prevenção, padronização e controles.")
    frame = db.dataframe("why5", project)
    if not frame.empty:
        show = frame.copy(); show["cadeia"] = show["chain"].apply(lambda x: " → ".join(json.loads(x)))
        st.dataframe(show[["problem", "cadeia", "root_cause", "evidence", "action", "owner", "due_date", "status"]], use_container_width=True, hide_index=True)


def render_cause_effect() -> None:
    st.header("Matriz causa e efeito")
    st.write("Edite as causas, os efeitos, os pesos e as relações. Use apenas 0, 1, 3 ou 9 nas relações.")
    causes_text = st.text_area("Causas potenciais — uma por linha", "Falha de padrão\nInspeção insuficiente\nEmbalagem inadequada")
    effects_text = st.text_area("Efeitos/CTQs e pesos — formato Efeito|Peso", "Parada de produção|10\nCusto|8\nQualidade|9")
    causes = [x.strip() for x in causes_text.splitlines() if x.strip()]
    effects = []
    for line in effects_text.splitlines():
        if "|" in line:
            name, weight = line.rsplit("|", 1)
            try: effects.append((name.strip(), float(weight)))
            except ValueError: pass
    if not causes or not effects:
        st.info("Informe causas e efeitos válidos.")
        return
    matrix = pd.DataFrame(0, index=causes, columns=[x[0] for x in effects]).reset_index(names="Causa")
    edited = st.data_editor(matrix, use_container_width=True, hide_index=True, key="cause_effect_editor")
    score = pd.Series(0.0, index=edited.index)
    for effect, weight in effects:
        relation = pd.to_numeric(edited[effect], errors="coerce").fillna(0)
        score += relation.where(relation.isin([0, 1, 3, 9]), 0) * weight
    ranking = pd.DataFrame({"Causa": edited["Causa"], "Pontuação": score}).sort_values("Pontuação", ascending=False)
    c1, c2 = st.columns(2)
    c1.dataframe(ranking, use_container_width=True, hide_index=True)
    c2.plotly_chart(px.bar(ranking, x="Pontuação", y="Causa", orientation="h", title="Prioridade das causas"), use_container_width=True)


def render_fmea(project: str) -> None:
    st.header("FMEA")
    with st.form("fmea_form", clear_on_submit=True):
        a, b, c = st.columns(3)
        process, step, mode = a.text_input("Processo"), b.text_input("Etapa"), c.text_input("Modo de falha")
        d, e, f = st.columns(3)
        effect, cause, control = d.text_input("Efeito"), e.text_input("Causa potencial"), f.text_input("Controle atual")
        g, h, i = st.columns(3)
        sev, occ, det = g.slider("Severidade", 1, 10, 5), h.slider("Ocorrência", 1, 10, 5), i.slider("Detecção", 1, 10, 5)
        j, k, l = st.columns(3)
        action, owner, due = j.text_input("Ação recomendada"), k.text_input("Responsável"), l.date_input("Prazo")
        m, n, o = st.columns(3)
        fs, fo, fd = m.slider("Severidade final", 1, 10, sev), n.slider("Ocorrência final", 1, 10, occ), o.slider("Detecção final", 1, 10, det)
        status = st.selectbox("Status", ["Não iniciado", "Em andamento", "Concluído", "Cancelado"])
        if st.form_submit_button("Adicionar ao FMEA", type="primary") and mode:
            db.execute("INSERT INTO fmea(project,process,step,failure_mode,effect,potential_cause,current_control,severity,occurrence,detection,recommended_action,owner,due_date,final_severity,final_occurrence,final_detection,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (project, process, step, mode, effect, cause, control, sev, occ, det, action, owner, str(due), fs, fo, fd, status))
            st.success("Modo de falha salvo.")
    frame = db.dataframe("fmea", project)
    if frame.empty: return
    frame["NPR inicial"] = frame.severity * frame.occurrence * frame.detection
    frame["NPR final"] = frame.final_severity * frame.final_occurrence * frame.final_detection
    frame["Redução %"] = np.where(frame["NPR inicial"] > 0, (frame["NPR inicial"] - frame["NPR final"]) / frame["NPR inicial"] * 100, 0)
    c1, c2, c3 = st.columns(3)
    c1.metric("Maior NPR", int(frame["NPR inicial"].max()))
    c2.metric("Severidade alta", int((frame.severity >= 9).sum()))
    c3.metric("Redução média", f"{frame['Redução %'].mean():.1f}%")
    st.plotly_chart(px.bar(frame.sort_values("NPR inicial"), x=["NPR inicial", "NPR final"], y="failure_mode", orientation="h", barmode="group", title="Risco inicial × residual"), use_container_width=True)
    st.dataframe(frame, use_container_width=True, hide_index=True)


ACTION_STATUS = ["Não iniciado", "Em andamento", "Aguardando", "Concluído", "Atrasado", "Cancelado"]


def render_actions(project: str) -> None:
    st.header("Plano de ação 5W2H")
    with st.form("action_form", clear_on_submit=True):
        what = st.text_input("What — O que será feito")
        why = st.text_input("Why — Por que será feito")
        a, b, c = st.columns(3)
        where, when, who = a.text_input("Where — Onde"), b.date_input("When — Quando"), c.text_input("Who — Responsável")
        how = st.text_area("How — Como será feito")
        d, e, f = st.columns(3)
        expected_cost, actual_cost, progress = d.number_input("Custo previsto", 0.0), e.number_input("Custo realizado", 0.0), f.slider("Percentual concluído", 0, 100, 0)
        status = st.selectbox("Status", ACTION_STATUS)
        evidence = st.text_input("Evidência da conclusão")
        g, h = st.columns(2)
        expected_result, actual_result = g.text_input("Resultado esperado"), h.text_input("Resultado obtido")
        if st.form_submit_button("Salvar ação", type="primary") and what:
            db.execute("INSERT INTO actions(project,what_action,why_action,where_action,when_date,who,how_action,expected_cost,actual_cost,status,progress,evidence,expected_result,actual_result) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (project, what, why, where, str(when), who, how, expected_cost, actual_cost, status, progress, evidence, expected_result, actual_result))
            st.success("Ação salva.")
    frame = db.dataframe("actions", project)
    if frame.empty: return
    frame["when_date"] = pd.to_datetime(frame["when_date"], errors="coerce")
    frame["dias"] = (frame["when_date"] - pd.Timestamp.today().normalize()).dt.days
    open_mask = ~frame.status.isin(["Concluído", "Cancelado"])
    frame.loc[open_mask & (frame.dias < 0), "status_calculado"] = "Atrasado"
    frame["status_calculado"] = frame["status_calculado"].fillna(frame.status)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ações", len(frame)); c2.metric("Concluídas", int((frame.status == "Concluído").sum()))
    c3.metric("Vencidas", int((open_mask & (frame.dias < 0)).sum())); c4.metric("Progresso médio", f"{frame.progress.mean():.1f}%")
    st.plotly_chart(px.timeline(frame, x_start="created_at", x_end="when_date", y="what_action", color="status_calculado", title="Cronograma de ações"), use_container_width=True)
    st.dataframe(frame, use_container_width=True, hide_index=True)


DMAIC_ITEMS = {
    "DEFINE": ["Problema", "Contexto", "Meta SMART", "Escopo", "Fora do escopo", "Cliente", "CTQ", "Equipe", "Cronograma", "SIPOC"],
    "MEASURE": ["Indicador principal", "Fórmula", "Baseline", "Meta", "Fonte", "Frequência", "Validação dos dados"],
    "ANALYZE": ["Pareto", "Estratificação", "Ishikawa", "5 Porquês", "Hipóteses", "Causas validadas", "Causas descartadas"],
    "IMPROVE": ["Soluções", "Matriz esforço × impacto", "Teste piloto", "5W2H", "Resultado do piloto", "Riscos"],
    "CONTROL": ["Indicadores", "Meta de controle", "Responsável", "Frequência", "Plano de reação", "Padronização", "Auditoria", "Lições aprendidas"],
}


def render_dmaic(project: str) -> None:
    st.header("Projeto DMAIC")
    saved = db.dataframe("dmaic", project)
    completion = {phase: 0.0 for phase in DMAIC_ITEMS}
    if not saved.empty:
        completion.update((saved.groupby("phase")["completed"].mean() * 100).to_dict())
    cols = st.columns(5)
    for col, phase in zip(cols, DMAIC_ITEMS): col.metric(phase, f"{completion.get(phase, 0):.0f}%")
    phase = st.tabs(list(DMAIC_ITEMS.keys()))
    existing = {(r.phase, r.item): r for r in saved.itertuples()} if not saved.empty else {}
    for tab, (phase_name, items) in zip(phase, DMAIC_ITEMS.items()):
        with tab:
            with st.form(f"dmaic_{phase_name}"):
                entries = []
                for item in items:
                    row = existing.get((phase_name, item))
                    done = st.checkbox(f"Concluir: {item}", value=bool(row.completed) if row else False, key=f"done_{phase_name}_{item}")
                    content = st.text_area(item, value=str(row.content) if row and row.content else "", key=f"content_{phase_name}_{item}")
                    entries.append((item, content, done))
                if st.form_submit_button(f"Salvar {phase_name}", type="primary"):
                    for item, content, done in entries:
                        db.execute("DELETE FROM dmaic WHERE project=? AND phase=? AND item=?", (project, phase_name, item))
                        db.execute("INSERT INTO dmaic(project,phase,item,content,completed) VALUES(?,?,?,?,?)", (project, phase_name, item, content, int(done)))
                    st.success("Fase salva.")


def render_before_after(df: pd.DataFrame) -> None:
    st.header("Comparação antes × depois")
    if "data" not in df:
        st.warning("Mapeie a data para realizar a comparação."); return
    metrics = [c for c in ["quantidade", "tempo_parada", "custo", "gravidade", "frequencia"] if c in df]
    if not metrics:
        st.warning("Mapeie uma variável numérica."); return
    a, b, c = st.columns(3)
    metric = a.selectbox("Indicador", metrics, format_func=lambda x: CANONICAL_FIELDS[x])
    min_date, max_date = df["data"].dropna().min().date(), df["data"].dropna().max().date()
    change = b.date_input("Data de implantação", value=min_date + (max_date - min_date) / 2, min_value=min_date, max_value=max_date)
    annual_factor = c.number_input("Fator de anualização", min_value=1.0, value=12.0)
    result = before_after(df, "data", metric, pd.Timestamp(change))
    if not result:
        st.warning("Não existem observações suficientes antes e depois da data escolhida."); return
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Média antes", f"{result['media_antes']:.2f}"); d2.metric("Média depois", f"{result['media_depois']:.2f}")
    d3.metric("Redução", f"{result['reducao']:.1f}%"); d4.metric("Projeção anual", f"{result['diferenca'] * annual_factor:.2f}")
    plot = df[["data", metric]].dropna().copy(); plot["Período"] = np.where(plot.data < pd.Timestamp(change), "Antes", "Depois")
    st.plotly_chart(px.box(plot, x="Período", y=metric, points="all", color="Período", title="Distribuição antes × depois"), use_container_width=True)
    st.caption(f"Amostras: {result['n_antes']} antes e {result['n_depois']} depois. O resultado é uma comparação descritiva; confirme outras mudanças simultâneas antes de atribuir causalidade.")


def render_effort_impact() -> None:
    st.header("Matriz esforço × impacto")
    initial = pd.DataFrame([{"Solução": "", "Impacto": 5, "Esforço": 5, "Custo": 0.0, "Risco": 5, "Viabilidade": 5}])
    edited = st.data_editor(initial, num_rows="dynamic", use_container_width=True, hide_index=True,
        column_config={x: st.column_config.NumberColumn(x, min_value=1, max_value=10) for x in ["Impacto", "Esforço", "Risco", "Viabilidade"]})
    valid = edited[edited["Solução"].astype(str).str.strip() != ""].copy()
    if valid.empty: return
    valid["Quadrante"] = np.select(
        [(valid.Impacto >= 5) & (valid.Esforço < 5), (valid.Impacto >= 5) & (valid.Esforço >= 5), (valid.Impacto < 5) & (valid.Esforço < 5)],
        ["Ganhos rápidos", "Projetos estratégicos", "Baixo impacto"], default="Reavaliar",
    )
    fig = px.scatter(valid, x="Esforço", y="Impacto", size="Custo", color="Quadrante", hover_name="Solução", range_x=[0, 11], range_y=[0, 11])
    fig.add_hline(y=5, line_dash="dash"); fig.add_vline(x=5, line_dash="dash")
    st.plotly_chart(fig, use_container_width=True)


def render_report(df: pd.DataFrame, project: str, filters: list[str]) -> None:
    st.header("Relatório executivo")
    st.write("O relatório usa apenas os dados filtrados neste momento e organiza os principais indicadores e Paretos em páginas A4 horizontais.")
    pdf = build_pdf(df, project, "; ".join(filters))
    st.download_button("Baixar relatório PDF", pdf, file_name=f"relatorio_{project.replace(' ', '_').lower()}.pdf", mime="application/pdf", type="primary")
    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("Baixar dados filtrados em CSV", csv, file_name="dados_filtrados.csv", mime="text/csv")


PAGES = ["Importação", "Visão executiva", "Ocorrências", "Pareto", "Estratificação", "Tendências", "Capabilidade", "Ishikawa — 6M", "5 Porquês", "Matriz causa e efeito", "FMEA", "Plano 5W2H", "DMAIC", "Antes × depois", "Esforço × impacto", "Relatório"]
project = st.sidebar.text_input("Projeto", value=st.session_state.get("project", "Projeto Lean Six Sigma"))
st.session_state.project = project
page = st.sidebar.radio("Navegação", PAGES)
st.sidebar.caption(f"Base: {st.session_state.get('source_name', 'nenhuma planilha carregada')}")

if page == "Importação":
    render_import()
else:
    base = data_required() if page in ["Visão executiva", "Ocorrências", "Pareto", "Estratificação", "Tendências", "Capabilidade", "Antes × depois", "Relatório"] else st.session_state.get("data", pd.DataFrame())
    if base is not None:
        filtered, filter_labels = apply_filters(base) if not base.empty else (base, [])
        if not base.empty:
            st.caption(f"{len(filtered):,} de {len(base):,} registro(s) após os filtros".replace(",", "."))
        if page == "Visão executiva": render_overview(filtered)
        elif page == "Ocorrências": render_occurrences(filtered)
        elif page == "Pareto": render_pareto(filtered)
        elif page == "Estratificação": render_stratification(filtered)
        elif page == "Tendências": render_trends(filtered)
        elif page == "Capabilidade": render_capability(filtered)
        elif page == "Ishikawa — 6M": render_ishikawa(project)
        elif page == "5 Porquês": render_five_whys(project)
        elif page == "Matriz causa e efeito": render_cause_effect()
        elif page == "FMEA": render_fmea(project)
        elif page == "Plano 5W2H": render_actions(project)
        elif page == "DMAIC": render_dmaic(project)
        elif page == "Antes × depois": render_before_after(filtered)
        elif page == "Esforço × impacto": render_effort_impact()
        elif page == "Relatório": render_report(filtered, project, filter_labels)
