from __future__ import annotations
import streamlit as st
import pandas as pd
from models import Filters
from view.base import BaseProfile
from queries import (
    get_dados_filtrados, get_metricas_qualidade_etl,
    get_tendencia_sessoes_fantasma, get_contagem_registos_nao_mapeados, get_anomalias_brutas,
)
from transforms import normalizar_dataframe, combine_flags_anomalia
from components import render_kpi, render_spacer, render_cabecalho_seccao, render_cobertura_dimensao
from plots import chart_tendencia_anomalias, chart_motivos_qualidade
from config import PLOTLY_CONFIG
from utils import fmt_int, fmt_pct, pct
from view.tooltips import COMPLETUDE, DADOS_EM_FALTA, RESERVAS, GHOST_TOTAL, HORARIO_INVULGAR


class QualidadeProfile(BaseProfile):
    def render(self, filters: Filters) -> None:
        self._h2("Qualidade dos Dados / ETL")

        ano_letivo = filters.get("ano_letivo")
        semestre   = filters.get("semestre")

        metrics     = get_metricas_qualidade_etl(
            ano_letivo=ano_letivo,
            semestre=semestre,
        )
        ghost_trend = get_tendencia_sessoes_fantasma(
            ano_escolar=ano_letivo,
            semestre=semestre,
        )
        unmapped    = get_contagem_registos_nao_mapeados(
            ano_letivo=ano_letivo,
            semestre=semestre,
        )
        total_ghost = unmapped.get("Ghost Sessions (0 Presenças)", 0)
        total_hora  = unmapped.get("Horário Invulgar (00h-08h)", 0)
        total       = metrics["total"]
        completude  = pct(metrics["completos"], total)

        k1, k2, k3, k4, k5, k6 = st.columns(6)
        with k1: render_kpi("Registos carregados", fmt_int(total), "📦")
        with k2: render_kpi("Completude", fmt_pct(completude), "✅", COMPLETUDE)
        with k3:
            render_kpi("Com dados em falta", fmt_int(metrics["incompletos"]), "🧩", DADOS_EM_FALTA)
            if st.button("🔍 Ver registos", key="btn_filtro_incompleto", use_container_width=True):
                st.session_state["qualidade_filtro_tipo"] = "incompleto"
        with k4: render_kpi("Reservas sem UC", fmt_int(metrics["reservas"]), "🗓️", RESERVAS)
        with k5:
            render_kpi("Sessões sem presenças", fmt_int(total_ghost), "👻", GHOST_TOTAL)
            if st.button("🔍 Ver registos", key="btn_filtro_ghost", use_container_width=True):
                st.session_state["qualidade_filtro_tipo"] = "ghost"
        with k6:
            render_kpi("Horário invulgar", fmt_int(total_hora), "🌙", HORARIO_INVULGAR)
            if st.button("🔍 Ver registos", key="btn_filtro_hora", use_container_width=True):
                st.session_state["qualidade_filtro_tipo"] = "hora"

        render_spacer(1.2)
        render_cabecalho_seccao("Porque é que há registos com dados em falta?")
        self._subtitle("Um registo pode ter mais do que um motivo. A percentagem é sobre o total de registos carregados.")
        st.plotly_chart(chart_motivos_qualidade(metrics["motivos"], total),
                        use_container_width=True, key="chart_motivos", config=PLOTLY_CONFIG)

        render_spacer(1.2)
        render_cabecalho_seccao("Evolução de Anomalias")
        st.plotly_chart(chart_tendencia_anomalias(ghost_trend),
                        use_container_width=True, key="chart_ghost_trend", config=PLOTLY_CONFIG)

        render_spacer()
        # Carrega os dados para calcular a cobertura das dimensões
        df = normalizar_dataframe(get_dados_filtrados(
            ano_letivo=ano_letivo,
            semestre=semestre,
        ))
        if not df.empty:
            render_cabecalho_seccao("Cobertura de Chaves Dimensionais")
            render_cobertura_dimensao(df)

        render_spacer()
        render_cabecalho_seccao("Registo de Anomalias (Auditoria)")

        filtro_tipo = st.session_state.get("qualidade_filtro_tipo")
        _labels_filtro = {
            "incompleto": "🧩 Registos com dados em falta",
            "ghost":    "👻 Sessões sem presenças",
            "uc_curso": "🚫 UC / Curso sem mapeamento",
            "hora":     "🌙 Horário Invulgar (00h-08h)",
        }
        if filtro_tipo:
            fcol1, fcol2 = st.columns([5, 1])
            with fcol1:
                st.info(f"🔎 A mostrar apenas: **{_labels_filtro.get(filtro_tipo, filtro_tipo)}**")
            with fcol2:
                if st.button("Limpar filtro", use_container_width=True):
                    st.session_state["qualidade_filtro_tipo"] = None
                    st.rerun()
        else:
            self._subtitle(
                "Últimos registos com algum alerta — sessões sem presenças, "
                "UC sem mapeamento, responsável indefinido ou horário invulgar (00h-08h). "
                "Usa os botões \"🔍 Ver registos\" nos KPI's acima para filtrar por tipo."
            )

        anomalies_df = normalizar_dataframe(get_anomalias_brutas(
            limit=100,
            ano_letivo=ano_letivo,
            semestre=semestre,
            tipo_anomalia=filtro_tipo,
        ))
        if anomalies_df.empty:
            st.success("Nenhuma anomalia encontrada nos registos atuais.")
            return

        display = anomalies_df.copy()
        if "DataCompleta" in display.columns:
            display["Data"] = display["DataCompleta"].dt.strftime("%d/%m/%Y")
        display["Início"]    = display.apply(lambda r: f"{int(r['Hora_Inicio']):02d}h", axis=1)
        display["Fim"]       = display.apply(lambda r: f"{int(r['Hora_Fim']):02d}h", axis=1)
        # Combina as flags de anomalia (ghost, UC N/D, curso N/D, responsável N/D) numa string
        display["Anomalias"] = display.apply(combine_flags_anomalia, axis=1)

        # Só mostra colunas que existam no DataFrame — evita KeyError se alguma estiver ausente
        audit_cols = [c for c in [
            "Data", "DiaSemana", "Início", "Fim", "Edificio", "Nome_Espaco",
            "Designacao_UC", "Docente_Responsavel",
            "Duracao_Minutos", "Numero_Presencas", "Anomalias",
        ] if c in display.columns]

        st.dataframe(
            display[audit_cols].rename(columns={
                "DiaSemana": "Dia", "Nome_Espaco": "Espaço", "Designacao_UC": "UC",
                "Nome_Curso": "Curso", "Docente_Responsavel": "Docente",
                "Duracao_Minutos": "Dur. (min)", "Numero_Presencas": "Presenças",
            }),
            use_container_width=True, hide_index=True, height=400,
        )

        render_spacer()
        st.markdown(
            "<p style='color:#94A3B8;font-size:0.85rem;'>"
            "Dados do Data Warehouse MySQL.</p>",
            unsafe_allow_html=True,
        )