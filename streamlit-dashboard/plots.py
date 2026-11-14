import plotly.graph_objects as go
import pandas as pd
import calendar
from config import COLORS, WEEKDAY_ORDER_FULL, WEEKDAY_PT, WEEKDAY_SHORT, WEEKDAY_SHORT_FULL, MESES_PT, DIAS_PT
from utils import fmt_int


def _layout_base(fig: go.Figure, title: str = "", height: int = 380) -> go.Figure:
    # Layout padrão aplicado a todos os gráficos — fundo transparente, fonte Inter
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=16, color="#1B2139", family="Inter, sans-serif"),
            x=0.02, y=0.96,
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#64748B", size=12),
        separators=", ",
        height=height,
        margin=dict(l=50, r=30, t=60, b=50),
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.25,
            xanchor="center", x=0.5, font=dict(size=11),
        ),
    )
    fig.update_xaxes(showgrid=True, gridcolor=COLORS["chart_grid"], gridwidth=0.5, zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["chart_grid"], gridwidth=0.5, zeroline=False)
    # Mapas de calor: margem à direita para o título da escala ("Sessões") não ficar cortado
    if any(getattr(t, "type", "") == "heatmap" for t in fig.data):
        fig.update_layout(margin=dict(r=80))
    return fig


def _build_heatmap_pivot(df: pd.DataFrame, value_col: str) -> tuple:
    # Constrói o pivot (DiaSemana × Hora) usado pelos mapas de calor
    day_order = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado"]
    df = df[df["DiaSemana"].isin(day_order)].copy()
    pivot = df.pivot_table(index="DiaSemana", columns="Hora_Inicio", values=value_col, fill_value=0)
    pivot = pivot.reindex([d for d in day_order if d in pivot.index])
    # Só mostra horas com pelo menos uma ocupação
    active_hours = sorted([h for h in pivot.columns if pivot[h].sum() > 0])
    if active_hours:
        pivot = pivot[active_hours]
    y_labels = [WEEKDAY_PT.get(d, d) for d in pivot.index]
    return pivot, y_labels, day_order


def chart_ocupacao_tempo(df: pd.DataFrame, granularity: str = "Mensal") -> go.Figure:
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Sem dados", showarrow=False, font=dict(size=16, color="#94A3B8"))
        return _layout_base(fig, "Ocupação ao longo do tempo")

    df = df.copy()
    # Agrupa por diário, semanal ou mensal conforme o que o user escolheu
    if granularity == "Diário":
        grouped = df.groupby("DataCompleta").size().reset_index(name="Total").sort_values("DataCompleta")
        x_col = "DataCompleta"
    elif granularity == "Semanal":
        df["Semana"] = df["DataCompleta"].dt.to_period("W").apply(lambda r: r.start_time.date())
        grouped = df.groupby("Semana").size().reset_index(name="Total").sort_values("Semana")
        x_col = "Semana"
    else:
        df["Mes_Periodo"] = df["DataCompleta"].dt.to_period("M").apply(lambda r: r.start_time.date())
        grouped = df.groupby("Mes_Periodo").size().reset_index(name="Total").sort_values("Mes_Periodo")
        x_col = "Mes_Periodo"

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=grouped[x_col], y=grouped["Total"],
        fill="tozeroy", fillcolor="rgba(59, 99, 251, 0.08)",
        line=dict(color=COLORS["primary"], width=2.5, shape="spline"),
        mode="lines", name="Ocupações",
        hovertemplate="<b>%{x}</b><br>Total: %{y:,.0f}<extra></extra>",
    ))
    fig = _layout_base(fig, "Ocupação ao longo do tempo", height=380)
    fig.update_xaxes(title_text="", tickfont=dict(color="#334155"))
    fig.update_yaxes(title_text="Nº Ocupações", tickfont=dict(color="#334155"))
    return fig

def chart_ocupacao_semana(df: pd.DataFrame) -> go.Figure:
    # Vista para semana específica — barras por dia da semana (Seg a Sáb)
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Sem dados", showarrow=False, font=dict(size=16, color="#94A3B8"))
        return _layout_base(fig, "Ocupação da Semana")

    day_order = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado"]
    day_labels = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]

    counts = (
        df[df["DiaSemana"].isin(day_order)]
        .groupby("DiaSemana")
        .size()
        .reindex(day_order, fill_value=0)
        .reset_index(name="Total")
    )
    counts["Label"] = day_labels[:len(counts)]

    fig = go.Figure(go.Bar(
        x=counts["DiaSemana"].map(dict(zip(day_order, day_labels))),
        y=counts["Total"],
        marker=dict(
            color=counts["Total"],
            colorscale=[[0, "#93C5FD"], [1, "#3B63FB"]],
            cornerradius=6,
        ),
        text=counts["Total"].apply(fmt_int),
        textposition="outside",
        textfont=dict(size=12, color="#1B2139"),
        hovertemplate="<b>%{x}</b><br>Sessões: %{y:,.0f}<extra></extra>",
    ))
    fig = _layout_base(fig, "Ocupação por Dia da Semana", height=380)
    fig.update_xaxes(title_text="", tickfont=dict(color="#334155"))
    fig.update_yaxes(title_text="Nº Sessões", tickfont=dict(color="#334155"))
    return fig


def _sem_dados(titulo: str, mensagem: str = "Sem dados para os filtros selecionados") -> go.Figure:
    # Figura vazia com uma mensagem explicativa, em vez de eixos sem nada
    fig = go.Figure()
    fig.add_annotation(text=mensagem, showarrow=False, font=dict(size=14, color="#94A3B8"))
    fig = _layout_base(fig, titulo)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return fig


def _encurtar(texto: str, max_chars: int = 28) -> str:
    # Encurta nomes longos nos eixos; o nome completo continua no tooltip
    texto = str(texto)
    return texto if len(texto) <= max_chars else texto[: max_chars - 1] + "…"


def _barras_horizontais(
    grouped: pd.DataFrame, label_col: str, titulo: str, x_title: str = "Nº Ocupações",
    cor: str | None = None, height: int = 380, mostrar_pct: bool = True,
) -> go.Figure:
    # Barras horizontais ordenadas (a maior em cima), com valor e percentagem no fim da barra.
    # Mais fáceis de comparar do que um donut com muitas fatias. "Outros" fica sempre em baixo.
    grouped = grouped.assign(_outros=grouped[label_col].eq("Outros"))
    grouped = grouped.sort_values(["_outros", "Total"], ascending=[False, True]).drop(columns="_outros")
    total = grouped["Total"].sum() or 1
    if mostrar_pct:
        texto = [f"{fmt_int(v)} ({v / total * 100:.0f}%)".replace(".", ",") for v in grouped["Total"]]
    else:
        texto = [fmt_int(v) for v in grouped["Total"]]
    fig = go.Figure(go.Bar(
        x=grouped["Total"],
        y=[_encurtar(v) for v in grouped[label_col]],
        customdata=grouped[label_col],
        orientation="h",
        marker=dict(color=cor or COLORS["primary"], cornerradius=4),
        text=texto, textposition="outside", cliponaxis=False,
        textfont=dict(size=11, color="#1B2139"),
        hovertemplate="<b>%{customdata}</b><br>Total: %{x:,.0f}<extra></extra>",
    ))
    fig = _layout_base(fig, titulo, height=height)
    fig.update_layout(showlegend=False, margin=dict(l=10, r=30))
    # Espaço à direita da barra maior para o rótulo "20 460 (37%)" não ficar cortado
    maximo = float(grouped["Total"].max() or 1)
    fig.update_xaxes(title_text=x_title, tickfont=dict(color="#334155"), range=[0, maximo * 1.3])
    fig.update_yaxes(title_text="", showgrid=False, tickfont=dict(color="#334155"), automargin=True)
    return fig


def chart_ocupacao_edificio(df: pd.DataFrame) -> go.Figure:
    titulo = "Ocupação por Edifício"
    if df.empty or "Edificio" not in df.columns:
        return _sem_dados(titulo)

    top = (df[df["Edificio"] != "N/D"].groupby("Edificio").size()
           .reset_index(name="Total").sort_values("Total", ascending=False))
    if top.empty:
        return _sem_dados(titulo)
    # A partir do 8.º edifício agrupa tudo em "Outros"
    if len(top) > 8:
        outros = pd.DataFrame({"Edificio": ["Outros"], "Total": [top.iloc[7:]["Total"].sum()]})
        top = pd.concat([top.head(7), outros], ignore_index=True)
    return _barras_horizontais(top, "Edificio", titulo)


def chart_heatmap_ocupacao(df_heatmap: pd.DataFrame) -> go.Figure:
    if df_heatmap.empty:
        fig = go.Figure()
        fig.add_annotation(text="Sem dados", showarrow=False, font=dict(size=16, color="#94A3B8"))
        return _layout_base(fig, "Mapa de Calor — Ocupação por Hora")

    pivot, y_labels, _ = _build_heatmap_pivot(df_heatmap, "Total_Ocupacoes")

    fig = go.Figure(data=go.Heatmap(
        z=pivot.values, x=[f"{h}h" for h in pivot.columns], y=y_labels,
        colorscale=[[0.0, "#EFF6FF"], [0.25, "#BFDBFE"], [0.5, "#60A5FA"], [0.75, "#3B63FB"], [1.0, "#1E3A8A"]],
        hovertemplate="<b>%{y}</b> às <b>%{x}</b><br>Ocupações: %{z:,.0f}<extra></extra>",
        showscale=True, colorbar=dict(title=dict(text="Ocupações", font=dict(size=11), side="right"), tickfont=dict(size=10), thickness=12, len=0.8),
    ))
    fig = _layout_base(fig, "Mapa de Calor — Ocupação por Hora", height=350)
    fig.update_yaxes(showgrid=False, autorange="reversed", tickfont=dict(color="#334155"))
    fig.update_xaxes(showgrid=False, side="top", tickfont=dict(color="#334155"))
    return fig


def chart_top_espacos(df: pd.DataFrame, top_n: int = 10) -> go.Figure:
    titulo = "Espaços com maior ocupação"
    if df.empty or "Nome_Espaco" not in df.columns:
        return _sem_dados(titulo)

    top = (df[df["Nome_Espaco"] != "N/D"].groupby("Nome_Espaco").size()
           .reset_index(name="Total").sort_values("Total", ascending=False).head(top_n))
    if top.empty:
        return _sem_dados(titulo)
    return _barras_horizontais(top, "Nome_Espaco", titulo, height=400, mostrar_pct=False)


def chart_bottom_espacos(df: pd.DataFrame, bottom_n: int = 10) -> go.Figure:
    # Ordena por horas ocupadas em vez de nº de sessões: com contagens, muitas salas
    # ficavam empatadas com 1 sessão e o gráfico não distinguia nada.
    # Os espaços sem nenhuma ocupação aparecem na página "Salas Vazias".
    titulo = "Espaços com menor ocupação (horas)"
    if df.empty or "Nome_Espaco" not in df.columns:
        return _sem_dados(titulo)

    validos = df[df["Nome_Espaco"] != "N/D"]
    if "Duracao_Minutos" in validos.columns:
        bottom = (validos.groupby("Nome_Espaco")["Duracao_Minutos"].sum() / 60).reset_index(name="Total")
        x_title = "Horas ocupadas"
    else:
        bottom = validos.groupby("Nome_Espaco").size().reset_index(name="Total")
        x_title = "Nº Ocupações"
    bottom = bottom.sort_values("Total", ascending=True).head(bottom_n)
    if bottom.empty:
        return _sem_dados(titulo)

    fig = _barras_horizontais(bottom, "Nome_Espaco", titulo, x_title=x_title,
                              cor=COLORS["barra_baixa"], height=400, mostrar_pct=False)
    # A menos ocupada fica em cima
    fig.update_yaxes(autorange="reversed")
    if x_title == "Horas ocupadas":
        fig.update_traces(
            text=[f"{v:.1f} h".replace(".", ",") for v in bottom.sort_values("Total")["Total"]],
            hovertemplate="<b>%{customdata}</b><br>%{x:.1f} h ocupadas<extra></extra>",
        )
    return fig


def chart_tipo_atividade(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Sem dados", showarrow=False, font=dict(size=16, color="#94A3B8"))
        return _layout_base(fig, "Distribuição por Tipo de Atividade")

    grouped = (df[df["Designacao_Atividade"] != "N/D"].groupby("Designacao_Atividade").size().reset_index(name="Total").sort_values("Total", ascending=False))
    fig = go.Figure(go.Bar(
        x=grouped["Designacao_Atividade"], y=grouped["Total"],
        marker=dict(color=COLORS["donut_palette"][:len(grouped)], cornerradius=6),
        text=grouped["Total"].apply(fmt_int), textposition="outside", textfont=dict(size=11),
        hovertemplate="<b>%{x}</b><br>Total: %{y:,.0f}<extra></extra>",
    ))
    fig = _layout_base(fig, "Distribuição por Tipo de Atividade", height=370)
    fig.update_xaxes(title_text="", tickangle=-30, tickfont=dict(color="#334155"))
    fig.update_yaxes(title_text="Nº Ocupações", tickfont=dict(color="#334155"))
    return fig


def chart_categoria_espaco(df: pd.DataFrame) -> go.Figure:
    titulo = "Ocupação por Categoria de Espaço"
    if df.empty or "Categoria_Espaco" not in df.columns:
        return _sem_dados(titulo)

    grouped = (df[df["Categoria_Espaco"] != "N/D"].groupby("Categoria_Espaco").size()
               .reset_index(name="Total"))
    if grouped.empty:
        return _sem_dados(titulo)
    return _barras_horizontais(grouped, "Categoria_Espaco", titulo, height=370)


def chart_periodo_dia(df: pd.DataFrame) -> go.Figure:
    if df.empty or "Periodo_Dia" not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text="Sem dados", showarrow=False, font=dict(size=16, color="#94A3B8"))
        return _layout_base(fig, "Ocupação por Período do Dia")

    period_order = ["Manhã", "Tarde", "Noite"]
    counts = df["Periodo_Dia"].value_counts().reindex(period_order, fill_value=0).reset_index()
    counts.columns = ["Periodo", "Total"]
    colors_map = COLORS["periodo"]

    fig = go.Figure(data=[go.Pie(
        labels=counts["Periodo"], values=counts["Total"], hole=0.4,
        marker=dict(colors=[colors_map.get(p, "#94A3B8") for p in counts["Periodo"]]),
        textinfo="label+percent", textposition="outside", textfont=dict(size=12),
        hovertemplate="<b>%{label}</b><br>Total: %{value:,.0f}<br>%{percent}<extra></extra>",
    )])
    fig = _layout_base(fig, "Ocupação por Período do Dia", height=370)
    return fig


def chart_heatmap_espaco_unico(df: pd.DataFrame) -> go.Figure:
    # Mapa de calor semanal para uma sala específica — células vazias ficam a verde claro
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Sem dados", showarrow=False, font=dict(size=16, color="#94A3B8"))
        return _layout_base(fig, "Ocupação Semanal — Sala")

    day_order = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado"]
    df = df[df["DiaSemana"].isin(day_order)].copy()
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Sem dados", showarrow=False, font=dict(size=16, color="#94A3B8"))
        return _layout_base(fig, "Ocupação Semanal — Sala")

    # Conta sessões por (dia, hora)
    grid = df.groupby(["DiaSemana", "Hora_Inicio"]).size().reset_index(name="count")
    pivot = grid.pivot_table(index="DiaSemana", columns="Hora_Inicio", values="count", fill_value=0)
    pivot = pivot.reindex([d for d in day_order if d in pivot.index])
    all_hours = sorted([h for h in pivot.columns])
    if all_hours:
        pivot = pivot[all_hours]

    y_labels = [WEEKDAY_PT.get(d, d) for d in pivot.index]

    # Verde claro para 0 sessões; azul crescente para mais sessões
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=[f"{h}h" for h in pivot.columns],
        y=y_labels,
        colorscale=[
            [0.0, "#F0FDF4"],
            [0.01, "#EFF6FF"],
            [0.25, "#BFDBFE"],
            [0.5,  "#60A5FA"],
            [0.75, "#3B63FB"],
            [1.0,  "#1E3A8A"],
        ],
        hovertemplate="<b>%{y}</b> às <b>%{x}</b><br>Sessões: %{z}<extra></extra>",
        showscale=True,
        colorbar=dict(title=dict(text="Sessões", font=dict(size=11), side="right"), tickfont=dict(size=10), thickness=12, len=0.8),
    ))
    fig = _layout_base(fig, "Ocupação Semanal — Sala", height=350)
    fig.update_yaxes(showgrid=False, autorange="reversed", tickfont=dict(color="#334155"))
    fig.update_xaxes(showgrid=False, side="top", dtick=1, tickfont=dict(color="#334155"))
    return fig


def chart_motivos_qualidade(motivos: dict, total: int) -> go.Figure:
    # Quantos registos têm cada tipo de dado em falta (um registo pode ter vários motivos)
    titulo = "Motivos de dados em falta"
    dados = pd.DataFrame({"Motivo": list(motivos.keys()), "Total": list(motivos.values())})
    dados = dados[dados["Total"] > 0]
    if dados.empty or not total:
        return _sem_dados(titulo, "Nenhum registo com dados em falta")
    dados = dados.sort_values("Total", ascending=True)
    fig = go.Figure(go.Bar(
        x=dados["Total"], y=dados["Motivo"], orientation="h",
        marker=dict(color=COLORS["nivel_medio"], cornerradius=4),
        text=[f"{fmt_int(v)} ({v / total * 100:.1f}%)".replace(".", ",") for v in dados["Total"]],
        textposition="outside", cliponaxis=False, textfont=dict(size=11, color="#1B2139"),
        hovertemplate="<b>%{y}</b><br>%{x:,.0f} registos<extra></extra>",
    ))
    fig = _layout_base(fig, titulo, height=max(220, 60 + 55 * len(dados) + 80))
    fig.update_layout(showlegend=False, margin=dict(l=10, r=30))
    fig.update_xaxes(title_text="Nº de registos", tickfont=dict(color="#334155"),
                     range=[0, float(dados["Total"].max()) * 1.35])
    fig.update_yaxes(title_text="", showgrid=False, tickfont=dict(color="#334155"), automargin=True)
    return fig


def chart_tendencia_anomalias(df: pd.DataFrame) -> go.Figure:
    # Evolução temporal das ghost sessions (aulas com 0 presenças)
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Sem dados de anomalias", showarrow=False,
                           font=dict(size=16, color="#94A3B8"))
        return _layout_base(fig, "Evolução de Anomalias")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["Periodo"],
        y=df["Ghost_Count"],
        mode="lines+markers",
        line=dict(color="#EF4444", width=2.5),
        marker=dict(size=8, color="#EF4444", line=dict(color="#991B1B", width=1)),
        fill="tozeroy",
        fillcolor="rgba(239, 68, 68, 0.08)",
        name="Sessões sem presenças",
        hovertemplate="<b>%{x}</b><br>Sessões sem presenças: %{y:,.0f}<extra></extra>",
    ))
    fig = _layout_base(fig, "Sessões sem presenças por mês", height=350)
    fig.update_xaxes(title_text="", tickfont=dict(color="#334155"))
    fig.update_yaxes(title_text="Nº de sessões", rangemode="tozero", tickfont=dict(color="#334155"))
    return fig


def chart_calendario_mensal(df: pd.DataFrame, year: int, month: int) -> go.Figure:
    # Calendário onde cada célula representa um dia do mês, cor indica nº de sessões
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Sem dados", showarrow=False, font=dict(size=16, color="#94A3B8"))
        return _layout_base(fig, f"Calendário {MESES_PT[month]} {year}")

    df = df.copy()
    df["DataCompleta"] = pd.to_datetime(df["DataCompleta"])
    # Conta sessões por dia
    daily = df.groupby(df["DataCompleta"].dt.date).size().reset_index(name="count")
    daily.columns = ["date", "count"]

    cal = calendar.monthcalendar(year, month)
    day_names = WEEKDAY_SHORT  # Seg a Sáb — sem domingo

    z = []
    hover_texts = []
    for week_idx, week in enumerate(cal):
        row = []
        hrow = []
        for day_idx, day_num in enumerate(week):
            if day_idx >= 6:  # ignora domingo
                continue
            if day_num == 0:
                # Dia fora do mês — célula vazia
                row.append(None)
                hrow.append("")
            else:
                d = pd.Timestamp(year=year, month=month, day=day_num)
                match = daily[daily["date"] == d.date()]
                val = int(match["count"].sum()) if not match.empty else 0
                row.append(val)
                hrow.append(
                    f"{d.strftime('%d/%m/%Y')} ({day_names[day_idx]})<br>"
                    f"Sessões: {val}"
                )
        z.append(row)
        hover_texts.append(hrow)

    week_labels = [f"S {i+1}" for i in range(len(cal))]

    fig = go.Figure(data=go.Heatmap(
        z=z,
        x=day_names,
        y=week_labels,
        text=hover_texts,
        hoverinfo="text",
        colorscale=[
            [0.0,    "#F0FDF4"],   # 0 sessões — verde claro
            [0.001,  "#EFF6FF"],   # 1 sessão  — azul muito claro
            [0.15,   "#BFDBFE"],
            [0.35,   "#60A5FA"],
            [0.55,   "#3B63FB"],
            [0.75,   "#1D4ED8"],
            [1.0,    "#1E3A8A"],
        ],
        showscale=True,
        colorbar=dict(
            title=dict(text="Sessões", font=dict(size=11), side="right"),
            tickfont=dict(size=10),
            thickness=12, len=0.7,
        ),
        xgap=4, ygap=4,
    ))

    fig.update_layout(
        title=dict(
            text=f"Calendário de Ocupação — {MESES_PT[month]} {year}",
            font=dict(size=16, color="#1B2139", family="Inter, sans-serif"),
            x=0.02, y=0.96,
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#64748B", size=12),
        separators=", ",
        height=300,
        margin=dict(l=40, r=80, t=60, b=30),
    )
    fig.update_xaxes(showgrid=False, side="top", tickfont=dict(size=11))
    fig.update_yaxes(showgrid=False, autorange="reversed", tickfont=dict(size=11))
    return fig


def chart_heatmap_critico(
    df: pd.DataFrame,
    total_rooms: int,
    low_threshold: float = 30.0,
    high_threshold: float = 70.0,
) -> go.Figure:
    # Mapa de calor com 3 níveis: claro (baixo), laranja (médio), vermelho escuro (alto)
    if df.empty or total_rooms == 0:
        fig = go.Figure()
        fig.add_annotation(text="Sem dados", showarrow=False, font=dict(size=16, color="#94A3B8"))
        return _layout_base(fig, "Ocupação Crítica por Horário")

    df = df.copy()
    # Só o horário letivo (8h–24h, a mesma base da taxa de utilização). As sessões entre
    # as 00h e as 08h são registos anómalos e já aparecem na página de Qualidade.
    if "Hora_Inicio" in df.columns:
        df = df[df["Hora_Inicio"] >= 8]
    if df.empty:
        return _sem_dados("Ocupação Crítica por Horário")
    # Percentagem de salas ocupadas em cada slot
    df["ratio"] = df["Salas_Ocupadas"] / total_rooms * 100
    pivot, y_labels, _ = _build_heatmap_pivot(df, "ratio")

    l = low_threshold / 100.0
    h = high_threshold / 100.0

    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=[f"{h}h" for h in pivot.columns],
        y=y_labels,
        colorscale=[
            [0.0,         COLORS["nivel_baixo"]],
            [l,           COLORS["nivel_baixo"]],
            [l + 0.001,   COLORS["nivel_medio"]],
            [h,           COLORS["nivel_medio"]],
            [h + 0.001,   COLORS["nivel_alto"]],
            [1.0,         COLORS["nivel_alto"]],
        ],
        xgap=1, ygap=1,
        zmin=0,
        zmax=100,
        hovertemplate="<b>%{y}</b> às <b>%{x}</b><br>Ocupação: %{z:.1f}%<extra></extra>",
        showscale=True,
        colorbar=dict(
            title=dict(text="Ocupação %", font=dict(size=11), side="right"),
            tickfont=dict(size=10),
            thickness=12, len=0.8,
            tickvals=[0, low_threshold, high_threshold, 100],
            ticktext=[f"0%", f"{low_threshold:.0f}%", f"{high_threshold:.0f}%", "100%"],
        ),
    ))

    fig = _layout_base(fig, "Ocupação Crítica por Horário", height=350)
    fig.update_yaxes(showgrid=False, autorange="reversed", tickfont=dict(color="#334155"))
    fig.update_xaxes(showgrid=False, side="top", tickfont=dict(color="#334155"))
    return fig


def chart_tendencia_comparacao(rooms_dict: dict) -> go.Figure:
    # Sessões por semana para várias salas — uma linha por sala.
    # Por semana (e não por dia) porque a série diária tinha demasiado ruído; as semanas
    # sem aulas (ex.: Natal) aparecem a 0 em vez de serem ligadas por uma reta.
    titulo = "Sessões por semana"
    if not rooms_dict:
        return _sem_dados(titulo, "Sem dados para comparação")

    palette = COLORS["donut_palette"]
    semanais = {}
    for room_name, room_df in rooms_dict.items():
        if room_df.empty:
            continue
        datas = pd.to_datetime(room_df["DataCompleta"])
        semana = (datas - pd.to_timedelta(datas.dt.weekday, unit="D")).dt.normalize()
        semanais[room_name] = semana.value_counts().sort_index()
    if not semanais:
        return _sem_dados(titulo, "Sem dados para comparação")

    inicio = min(s.index.min() for s in semanais.values())
    fim    = max(s.index.max() for s in semanais.values())
    todas  = pd.date_range(inicio, fim, freq="W-MON")

    fig = go.Figure()
    for i, (room_name, serie) in enumerate(semanais.items()):
        serie = serie.reindex(todas, fill_value=0)
        fig.add_trace(go.Scatter(
            x=serie.index, y=serie.values,
            mode="lines+markers", name=room_name,
            line=dict(color=palette[i % len(palette)], width=2.5),
            marker=dict(size=6),
            customdata=serie.index.strftime("%d/%m/%Y"),
            hovertemplate=f"<b>{room_name}</b><br>Semana de %{{customdata}}<br>Sessões: %{{y}}<extra></extra>",
        ))

    fig = _layout_base(fig, titulo, height=420)
    fig.update_layout(
        margin=dict(l=50, r=30, t=60, b=90),
        legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="center", x=0.5, font=dict(size=11)),
    )
    # Datas no formato dd/mm (evita os nomes dos meses em inglês do Plotly)
    fig.update_xaxes(title_text="", tickformat="%d/%m", tickfont=dict(color="#334155"))
    fig.update_yaxes(title_text="Nº Sessões", rangemode="tozero", tickfont=dict(color="#334155"))
    return fig


def chart_sessoes_por_sala(df: pd.DataFrame) -> go.Figure:
    # Barras da página de comparação — altura ajustada ao número de salas
    titulo = "Sessões por sala"
    if df.empty or "Nome_Espaco" not in df.columns:
        return _sem_dados(titulo)
    grouped = df.groupby("Nome_Espaco").size().reset_index(name="Total")
    altura = min(420, 120 + 55 * len(grouped))
    fig = _barras_horizontais(grouped, "Nome_Espaco", titulo, x_title="Nº Sessões",
                              height=altura, mostrar_pct=False)
    # Cada sala com a mesma cor da sua linha no gráfico de tendência
    # (a ordem de chegada das salas é a mesma nos dois gráficos)
    palette = COLORS["donut_palette"]
    cor_sala = {sala: palette[i % len(palette)] for i, sala in enumerate(df["Nome_Espaco"].unique())}
    fig.update_traces(marker_color=[cor_sala.get(s, COLORS["primary"]) for s in fig.data[0].customdata])
    return fig


def _get_mapa_cores(df: pd.DataFrame) -> dict:
    # Atribui uma cor estável a cada UC — ordem alfabética para ser consistente entre vistas
    keys = sorted(df["Designacao_UC"].dropna().unique().tolist())
    return {k: COLORS["turno_palette"][i % len(COLORS["turno_palette"])] for i, k in enumerate(keys)}


def _time_to_hour(hora: int, minuto: int) -> float:
    # Converte hora + minuto para decimal (ex: 9h30 → 9.5)
    return hora + minuto / 60.0


def _fmt_time(hora: int, minuto: int) -> str:
    return f"{int(hora):02d}:{int(minuto):02d}"

def _fmt_date_pt(date: pd.Timestamp) -> str:
    return f"{DIAS_PT[date.weekday()]}, {date.day:02d} de {MESES_PT[date.month]} de {date.year}"

def _wrap_text(text: str, max_chars: int = 18, max_lines: int | None = None) -> str:
    # Parte texto longo em várias linhas para caber nas células do calendário.
    # Palavras maiores do que a linha são cortadas; se houver mais linhas do que
    # max_lines, a última termina em "…".
    text = str(text)
    if len(text) <= max_chars:
        return text
    words = []
    for w in text.split():
        while len(w) > max_chars:
            words.append(w[: max_chars - 1] + "-")
            w = w[max_chars - 1:]
        words.append(w)
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 > max_chars and cur:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        ultima = lines[-1]
        lines[-1] = (ultima[: max_chars - 1] if len(ultima) >= max_chars else ultima) + "…"
    return "<br>".join(lines)


def _nome_uc_legivel(uc: object) -> str:
    # Mostra as reservas sem UC com um nome legível em vez do código interno
    uc = str(uc or "")
    if uc.startswith("SEM_UNIDADE"):
        return "Reserva administrativa"
    if uc in ("", "N/D", "nan"):
        return "Sem UC"
    return uc


def _layout_base_calendario(fig: go.Figure, title: str, height: int) -> go.Figure:
    # Layout base para as vistas de calendário (dia, semana, mês)
    # Margem do topo aumentada para o título não tapar o cabeçalho dos dias
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color="#1B2139", family="Inter, sans-serif"), x=0.01, y=0.97),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#FAFBFF",
        height=height,
        margin=dict(l=60, r=20, t=70, b=30),
        showlegend=False,
        font=dict(family="Inter, sans-serif", size=11, color="#334155"),
    )
    return fig


def chart_calendario_dia(df: pd.DataFrame, date: pd.Timestamp) -> go.Figure:
    # Vista diária — uma coluna com os blocos de aulas ordenados por hora
    day_df = df[df["DataCompleta"].dt.date == date.date()].copy()
    fig = go.Figure()

    y_min, y_max = 8, 24
    color_map = _get_mapa_cores(df)

    # Linhas de grelha hora a hora
    for h in range(y_min, y_max + 1):
        fig.add_shape(type="line", x0=0, x1=1, y0=h, y1=h,
                      line=dict(color="#94A3B8", width=1))
        fig.add_annotation(x=-0.02, y=h, text=f"{h}h", showarrow=False,
                           font=dict(size=10, color="#94A3B8"), xref="paper", yref="y", xanchor="right")

    if day_df.empty:
        fig.add_annotation(text="Sem aulas neste dia", x=0.5, y=(y_min + y_max) / 2,
                           showarrow=False, font=dict(size=14, color="#94A3B8"), xref="paper", yref="y")
    else:
        for _, row in day_df.iterrows():
            t_start = _time_to_hour(row["Hora_Inicio"], row["Minuto_Inicio"])
            t_end   = _time_to_hour(row["Hora_Fim"],   row["Minuto_Fim"])

            # Se o fim for antes ou igual ao início, assume meia-noite
            if t_end <= t_start:
                t_end = 24.0

            color = color_map.get(row.get("Designacao_UC", ""), "#3B63FB")
            label = f"{_wrap_text(_nome_uc_legivel(row.get('Designacao_UC', '')), 40)}<br>" \
                    f"<span style='font-size:10px'>{row.get('Designacao_Turno', '')} · " \
                    f"{_fmt_time(row['Hora_Inicio'], row['Minuto_Inicio'])}–{_fmt_time(row['Hora_Fim'], row['Minuto_Fim'])}</span>"
            hover = (f"<b>{row.get('Designacao_UC', '')}</b><br>"
                     f"Turno: {row.get('Designacao_Turno', 'N/D')}<br>"
                     f"Hora: {_fmt_time(row['Hora_Inicio'], row['Minuto_Inicio'])} – {_fmt_time(row['Hora_Fim'], row['Minuto_Fim'])}<br>"
                     f"Docente: {row.get('Docente_Responsavel', 'N/D')}<br>"
                     f"Sala: {row.get('Nome_Espaco', 'N/D')}")
            fig.add_shape(type="rect", x0=0.05, x1=0.95, y0=t_start, y1=t_end,
                          fillcolor=color, opacity=0.85, line=dict(color="white", width=1.5),
                          layer="above")
            fig.add_annotation(
                x=0.5, y=(t_start + t_end) / 2,
                text=label,
                showarrow=False,
                font=dict(size=11, color="white"),
                xref="paper", yref="y",
                align="center",
                xanchor="center", yanchor="middle",
                bgcolor="rgba(0,0,0,0)",
                borderpad=3,
            )

    fig.update_xaxes(visible=False, range=[0, 1])
    fig.update_yaxes(range=[y_max, y_min], showgrid=False, showticklabels=False, zeroline=False)
    fig = _layout_base_calendario(fig, f"📅 {_fmt_date_pt(date)}", height=700)
    return fig


def chart_calendario_semana(df: pd.DataFrame, week_dates: list[pd.Timestamp], title: str = "") -> go.Figure:
    if not df.empty and "DataCompleta" in df.columns:
        df["DataCompleta"] = pd.to_datetime(df["DataCompleta"], errors='coerce')
    # Vista semanal — uma coluna por dia, blocos de aulas sobrepostos na grelha horária
    fig = go.Figure()
    color_map = _get_mapa_cores(df)

    y_min, y_max = 8, 24
    n_days = len(week_dates)

    # Cabeçalho com o nome curto do dia e o número — ponto azul se tiver aulas
    for col_i, day_ts in enumerate(week_dates):
        x_center = col_i + 0.5
        day_df = df[df["DataCompleta"].dt.date == day_ts.date()]
        dot = " 🔵" if not day_df.empty else ""
        fig.add_annotation(
            x=x_center, y=y_max + 0.5,
            text=f"<b>{WEEKDAY_SHORT_FULL[day_ts.weekday()]}</b><br><span style='font-size:12px'>{day_ts.day}</span>{dot}",
            showarrow=False, font=dict(size=12, color="#1B2139"), yref="y", xref="x",
            align="center",
        )

    # Grelha de horas
    for h in range(y_min, y_max + 1):
        fig.add_shape(type="line", x0=0, x1=n_days, y0=h, y1=h,
                      line=dict(color="#94A3B8", width=0.8))
        fig.add_annotation(x=-0.15, y=h, text=f"{h}h", showarrow=False,
                           font=dict(size=9, color="#94A3B8"), xref="x", yref="y", xanchor="right")

    # Separadores verticais entre dias
    for col_i in range(n_days + 1):
        fig.add_shape(type="line", x0=col_i, x1=col_i, y0=y_min, y1=y_max,
                      line=dict(color="#94A3B8", width=1))

    # Blocos de eventos
    for col_i, day_ts in enumerate(week_dates):
        day_df = df[df["DataCompleta"].dt.date == day_ts.date()].copy()
        if day_df.empty:
            continue
        for _, row in day_df.iterrows():
            t_start = _time_to_hour(row["Hora_Inicio"], row["Minuto_Inicio"])
            t_end   = _time_to_hour(row["Hora_Fim"],   row["Minuto_Fim"])

            # Se o fim for antes ou igual ao início, assume meia-noite
            if t_end <= t_start:
                t_end = 24.0

            dur_horas = t_end - t_start

            color    = color_map.get(row.get("Designacao_UC", ""), "#3B63FB")
            uc_short = _nome_uc_legivel(row.get("Designacao_UC", ""))
            turno    = str(row.get("Designacao_Turno", ""))
            hora     = f"{_fmt_time(row['Hora_Inicio'], row['Minuto_Inicio'])}–{_fmt_time(row['Hora_Fim'], row['Minuto_Fim'])}"
            # Sem turno conhecido mostra só a hora
            rodape   = hora if turno in ("", "N/D", "nan") else f"{turno} · {hora}"

            # Texto e fonte adaptados à altura do bloco. A largura de uma coluna da semana
            # só leva ~20 caracteres; com mais, o texto ficava cortado dos dois lados.
            max_chars = 16 if dur_horas < 1.0 else 20
            max_linhas = 1 if dur_horas < 1.0 else 2 if dur_horas < 2.0 else 3
            font_size = 10 if dur_horas < 1.0 else 12
            uc_wrapped = _wrap_text(uc_short, max_chars, max_linhas)
            label      = f"{uc_wrapped}<br>{rodape}"

            hover = (f"<b>{row.get('Designacao_UC', '')}</b><br>"
                     f"Turno: {turno}<br>"
                     f"{_fmt_time(row['Hora_Inicio'], row['Minuto_Inicio'])} – {_fmt_time(row['Hora_Fim'], row['Minuto_Fim'])}<br>"
                     f"Docente: {row.get('Docente_Responsavel', 'N/D')}<br>"
                     f"Sala: {row.get('Nome_Espaco', 'N/D')}")

            x0 = col_i + 0.05
            x1 = col_i + 0.95
            fig.add_shape(type="rect", x0=x0, x1=x1, y0=t_start, y1=t_end,
                          fillcolor=color, opacity=0.88,
                          line=dict(color="white", width=1.2), layer="above")
            fig.add_annotation(
                x=(x0 + x1) / 2,
                y=(t_start + t_end) / 2,
                text=label,
                showarrow=False,
                font=dict(size=font_size, color="white"),
                xref="x", yref="y",
                align="center",
                xanchor="center", yanchor="middle",
                bgcolor="rgba(0,0,0,0)",
                borderpad=2,
            )

    fig.update_xaxes(range=[-0.3, n_days], showgrid=False, showticklabels=False, zeroline=False)
    fig.update_yaxes(range=[y_max + 1, y_min - 0.5], showgrid=False, showticklabels=False, zeroline=False)
    fig = _layout_base_calendario(fig, title or "📅 Vista Semanal", height=750)
    return fig

def chart_calendario_mes(df: pd.DataFrame, year: int, month: int) -> go.Figure:
    import calendar as cal_lib
    color_map = _get_mapa_cores(df)

    fig = go.Figure()
    cal_matrix = cal_lib.monthcalendar(year, month)

    n_weeks = len(cal_matrix)

    # Filtra apenas os dias do mês corrente para calcular a altura correta
    df_mes = df[
        (pd.to_datetime(df["DataCompleta"]).dt.year == year) &
        (pd.to_datetime(df["DataCompleta"]).dt.month == month)
    ]

    # Pré-agrupa sessões por data — evita filtrar o DataFrame inteiro para cada dia
    daily_groups = df_mes.groupby(df_mes["DataCompleta"].dt.date)
    daily_counts = daily_groups.size().to_dict()

    # Altura dinâmica baseada no dia com mais eventos do mês — célula dimensionada pelo dia mais cheio
    max_events_in_day = max(daily_counts.values(), default=1)
    cell_height_px    = 30 + max_events_in_day * 22
    total_height      = 80 + n_weeks * cell_height_px
    cell_h            = 1.0 / n_weeks
    day_names         = WEEKDAY_SHORT  # Seg a Sáb — sem domingo

    # Cabeçalho com os nomes dos dias
    for col_i, dname in enumerate(day_names):
        fig.add_annotation(x=col_i + 0.5, y=1.04, text=f"<b>{dname}</b>",
                           showarrow=False, font=dict(size=16, color="#475569"),
                           xref="x", yref="paper", xanchor="center")

    for row_i, week in enumerate(cal_matrix):
        y_top    = 1.0 - row_i * cell_h
        y_bottom = y_top - cell_h

        for col_i, day_num in enumerate(week):
            if col_i >= 6:  # ignora domingo
                continue

            x0, x1 = col_i, col_i + 1
            fig.add_shape(type="rect", x0=x0, x1=x1, y0=y_bottom, y1=y_top,
                          fillcolor="white", line=dict(color="#94A3B8", width=1), layer="below")

            if day_num == 0:
                # Dia fora do mês — fundo cinzento
                fig.add_shape(type="rect", x0=x0, x1=x1, y0=y_bottom, y1=y_top,
                              fillcolor="#F8FAFC", line=dict(color="#94A3B8", width=1), layer="below")
                continue

            # Número do dia no canto superior esquerdo da célula
            fig.add_annotation(x=x0 + 0.08, y=y_top - 0.008,
                               text=f"<b>{day_num}</b>",
                               showarrow=False, font=dict(size=11, color="#334155"),
                               xref="x", yref="paper", xanchor="left", yanchor="top")

            day_ts = pd.Timestamp(year=year, month=month, day=day_num).date()
            day_df = daily_groups.get_group(day_ts).sort_values("Hora_Inicio") if day_ts in daily_groups.groups else pd.DataFrame()

            if len(day_df) == 0:
                continue

            header_frac = 0.12
            padding     = 0.015 
            gap         = 0.004
            bottom_pad  = 0.008
            available   = cell_h - header_frac * cell_h - padding - bottom_pad
            ev_h        = available / max(max_events_in_day, 1)

            for ev_i, (_, row) in enumerate(day_df.iterrows()):
                color    = color_map.get(row.get("Designacao_UC", ""), "#3B63FB")
                ev_y_top = y_top - header_frac * cell_h - padding - ev_i * (ev_h + gap)
                ev_y_bot = ev_y_top - ev_h + gap

                hora        = f"{_fmt_time(row['Hora_Inicio'], row['Minuto_Inicio'])}–{_fmt_time(row['Hora_Fim'], row['Minuto_Fim'])}"
                uc_short    = _nome_uc_legivel(row.get("Designacao_UC", ""))[:14]
                turno_short = str(row.get("Designacao_Turno", ""))[:8]
                label       = f"{hora} {uc_short} {turno_short}"

                fig.add_shape(type="rect",
                              x0=x0 + 0.06, x1=x1 - 0.06,
                              y0=ev_y_bot, y1=ev_y_top,
                              fillcolor=color, opacity=0.85,
                              line=dict(color="white", width=0.5), layer="above")
                fig.add_annotation(
                    x=(x0 + x1) / 2, y=(ev_y_top + ev_y_bot) / 2,
                    text=label,
                    showarrow=False,
                    font=dict(size=10, color="white"),
                    xref="x", yref="paper",
                    align="center",
                    xanchor="center", yanchor="middle",
                    bgcolor="rgba(0,0,0,0)",
                    borderpad=1,
                )

    fig.update_xaxes(range=[0, 6], showgrid=False, showticklabels=False, zeroline=False)
    fig.update_yaxes(range=[0, 1], showgrid=False, showticklabels=False, zeroline=False)
    fig = _layout_base_calendario(fig, f"📅 {MESES_PT[month]} {year}", height=total_height)
    fig.update_layout(margin=dict(l=10, r=10, t=70, b=10))
    return fig