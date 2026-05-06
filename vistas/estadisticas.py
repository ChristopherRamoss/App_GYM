import streamlit as st
import sqlite3
import pandas as pd
import altair as alt
from datetime import datetime, timedelta, date
import calendar
import api_utils

conn = sqlite3.connect("gym_data.db", check_same_thread=False)
c    = conn.cursor()

TRAD = {
    "abdominals":"Abdominales","abductors":"Abductores","adductors":"Aductores",
    "biceps":"Bíceps","calves":"Pantorrillas","chest":"Pecho",
    "forearms":"Antebrazos","glutes":"Glúteos","hamstrings":"Isquiotibiales",
    "lats":"Dorsales","lower back":"Esp. Baja","middle back":"Esp. Media",
    "neck":"Cuello","quadriceps":"Cuádriceps","shoulders":"Hombros",
    "traps":"Trapecios","triceps":"Tríceps",
}

biblioteca_completa = api_utils.cargar_biblioteca_completa()

def m_es(m): return TRAD.get(m, m.title())

st.title("📊 Estadísticas")

# ── Tabs principales para no saturar la pantalla ──────────────────
tab_resumen, tab_avanzado, tab_calendario, tab_prs = st.tabs([
    "📈 Resumen", "🔬 Análisis Avanzado", "📅 Calendario", "🏆 Records"
])

# ══════════════════════════════════════════════════════════════════
# DATOS BASE
# ══════════════════════════════════════════════════════════════════
hoy      = date.today()
lunes    = hoy - timedelta(days=hoy.weekday())
hace_28  = hoy - timedelta(days=28)

df_todo = pd.read_sql_query(
    """SELECT e.ejercicio, e.peso, e.reps, e.fecha, s.nombre_rutina
       FROM entreno e LEFT JOIN sesiones s ON e.sesion_id = s.id
       ORDER BY e.fecha""",
    conn
)

df_semana = pd.DataFrame()
df_mes    = pd.DataFrame()

if not df_todo.empty:
    df_todo['fecha_dt'] = pd.to_datetime(df_todo['fecha'])
    df_todo['volumen']  = df_todo['peso'] * df_todo['reps']
    df_todo['dia']      = df_todo['fecha_dt'].dt.date
    df_semana = df_todo[df_todo['dia'] >= lunes]
    df_mes    = df_todo[df_todo['dia'] >= hace_28]

# ══════════════════════════════════════════════════════════════════
# TAB 1 — RESUMEN SEMANAL
# ══════════════════════════════════════════════════════════════════
with tab_resumen:
    if df_semana.empty:
        st.info("Sin entrenamientos esta semana. ¡Dale! 💪")
    else:
        # Métricas rápidas
        vol_sem   = df_semana['volumen'].sum()
        series_n  = len(df_semana)
        dias_n    = df_semana['dia'].nunique()
        col1, col2, col3 = st.columns(3)
        col1.metric("💪 Volumen semana",  f"{vol_sem:,.0f} lb")
        col2.metric("📋 Series totales",  series_n)
        col3.metric("📅 Días entrenados", dias_n)

        st.divider()

        # ── Grupos musculares esta semana ──────────────────────
        st.subheader("Grupos musculares esta semana")
        conteo_m = {}
        for _, r in df_semana.iterrows():
            info = biblioteca_completa.get(r['ejercicio'], {})
            for m in info.get("primaryMuscles", []):
                me = m_es(m)
                conteo_m[me] = conteo_m.get(me, 0) + 1

        if conteo_m:
            df_m = pd.DataFrame(list(conteo_m.items()), columns=["Músculo","Series"]).sort_values("Series", ascending=False)
            chart = alt.Chart(df_m).mark_bar(
                color="#3b82f6", cornerRadiusTopLeft=4, cornerRadiusTopRight=4
            ).encode(
                x=alt.X("Músculo:N", sort="-y", title=None, axis=alt.Axis(labelAngle=-30)),
                y=alt.Y("Series:Q", title="Series"),
                tooltip=["Músculo","Series"],
                color=alt.condition(
                    alt.datum.Series >= df_m['Series'].max() * 0.8,
                    alt.value("#ef4444"), alt.value("#3b82f6")
                )
            ).properties(height=240)
            st.altair_chart(chart, use_container_width=True)

        # ── Ejercicios más frecuentes ──────────────────────────
        st.subheader("Ejercicios más frecuentes esta semana")
        freq = df_semana.groupby("ejercicio").size().reset_index(name="series") \
                        .sort_values("series", ascending=False).head(10)
        if not freq.empty:
            chart_ej = alt.Chart(freq).mark_bar(
                color="#22c55e", cornerRadiusTopLeft=4, cornerRadiusTopRight=4
            ).encode(
                x=alt.X("series:Q", title="Series"),
                y=alt.Y("ejercicio:N", sort="-x", title=None),
                tooltip=["ejercicio","series"]
            ).properties(height=max(180, len(freq)*26))
            st.altair_chart(chart_ej, use_container_width=True)

        # ── Volumen por día esta semana ────────────────────────
        st.subheader("Volumen diario esta semana")
        vol_dia = df_semana.groupby("dia")["volumen"].sum().reset_index()
        vol_dia.columns = ["Día","Volumen"]
        vol_dia["Día"] = pd.to_datetime(vol_dia["Día"])
        dias_es = {0:"Lun",1:"Mar",2:"Mié",3:"Jue",4:"Vie",5:"Sáb",6:"Dom"}
        vol_dia["DíaNombre"] = vol_dia["Día"].dt.weekday.map(dias_es)
        chart_vol = alt.Chart(vol_dia).mark_bar(
            color="#f59e0b", cornerRadiusTopLeft=4, cornerRadiusTopRight=4
        ).encode(
            x=alt.X("DíaNombre:N", sort=list(dias_es.values()), title=None),
            y=alt.Y("Volumen:Q", title="lb × reps"),
            tooltip=["DíaNombre","Volumen"]
        ).properties(height=200)
        st.altair_chart(chart_vol, use_container_width=True)

# ══════════════════════════════════════════════════════════════════
# TAB 2 — ANÁLISIS AVANZADO
# ══════════════════════════════════════════════════════════════════
with tab_avanzado:
    if df_mes.empty:
        st.info("Necesitas al menos una sesión en los últimos 28 días.")
    else:
        st.subheader("🔬 Últimos 28 días")

        # ── A. Volumen acumulado por grupo muscular ────────────
        st.markdown("##### Volumen por grupo muscular")
        vol_musculo = {}
        for _, r in df_mes.iterrows():
            info = biblioteca_completa.get(r['ejercicio'], {})
            for m in info.get("primaryMuscles", []):
                me = m_es(m)
                vol_musculo[me] = vol_musculo.get(me, 0.0) + r['volumen']

        if vol_musculo:
            df_vm = pd.DataFrame(list(vol_musculo.items()), columns=["Músculo","Volumen"]) \
                      .sort_values("Volumen", ascending=False)
            df_vm["Volumen_k"] = (df_vm["Volumen"] / 1000).round(1)
            chart_vm = alt.Chart(df_vm).mark_bar(
                cornerRadiusTopLeft=4, cornerRadiusTopRight=4
            ).encode(
                x=alt.X("Músculo:N", sort="-y", title=None, axis=alt.Axis(labelAngle=-35)),
                y=alt.Y("Volumen:Q", title="lb × reps"),
                color=alt.Color("Volumen:Q", scale=alt.Scale(scheme="blues"), legend=None),
                tooltip=["Músculo", alt.Tooltip("Volumen:Q", format=",.0f", title="Volumen")]
            ).properties(height=260)
            st.altair_chart(chart_vm, use_container_width=True)

        st.divider()

        # ── B. Frecuencia semanal por músculo ─────────────────
        st.markdown("##### Frecuencia semanal por grupo muscular")
        st.caption("Promedio de días por semana que se trabajó cada músculo")

        df_mes_copy = df_mes.copy()
        df_mes_copy["semana"] = df_mes_copy["fecha_dt"].dt.isocalendar().week

        freq_sem = {}
        for _, r in df_mes_copy.iterrows():
            info = biblioteca_completa.get(r['ejercicio'], {})
            for m in info.get("primaryMuscles", []):
                me = m_es(m)
                if me not in freq_sem:
                    freq_sem[me] = set()
                freq_sem[me].add((r["semana"], r["dia"]))

        n_semanas = max(1, df_mes_copy["semana"].nunique())
        freq_prom = {m: len(dias) / n_semanas for m, dias in freq_sem.items()}

        if freq_prom:
            df_fp = pd.DataFrame(list(freq_prom.items()), columns=["Músculo","Días/sem"]) \
                      .sort_values("Días/sem", ascending=False)
            chart_fp = alt.Chart(df_fp).mark_bar(
                color="#a855f7", cornerRadiusTopLeft=4, cornerRadiusTopRight=4
            ).encode(
                x=alt.X("Músculo:N", sort="-y", title=None, axis=alt.Axis(labelAngle=-35)),
                y=alt.Y("Días/sem:Q", title="Días por semana", scale=alt.Scale(domain=[0,7])),
                tooltip=["Músculo", alt.Tooltip("Días/sem:Q", format=".1f")]
            ).properties(height=220)
            # Línea de referencia: 2 días/sem
            ref = alt.Chart(pd.DataFrame({"y":[2]})).mark_rule(
                color="#ef4444", strokeDash=[6,3], opacity=0.7
            ).encode(y="y:Q")
            st.altair_chart(chart_fp + ref, use_container_width=True)
            st.caption("🔴 Línea = 2 días/semana (referencia óptima de frecuencia)")

        st.divider()

        # ── C. Intensidad promedio por ejercicio ──────────────
        st.markdown("##### Intensidad promedio (últimos 28 días)")
        st.caption("Peso promedio usado por ejercicio — top 15")

        intens = df_mes.groupby("ejercicio")["peso"].mean().reset_index()
        intens.columns = ["Ejercicio", "Peso Prom (lb)"]
        intens = intens.sort_values("Peso Prom (lb)", ascending=False).head(15)

        if not intens.empty:
            chart_int = alt.Chart(intens).mark_bar(
                color="#f97316", cornerRadiusTopLeft=4, cornerRadiusTopRight=4
            ).encode(
                x=alt.X("Peso Prom (lb):Q", title="lb promedio"),
                y=alt.Y("Ejercicio:N", sort="-x", title=None),
                tooltip=["Ejercicio", alt.Tooltip("Peso Prom (lb):Q", format=".1f")]
            ).properties(height=max(200, len(intens)*26))
            st.altair_chart(chart_int, use_container_width=True)

        st.divider()

        # ── D. Tendencia de volumen semanal (8 semanas) ───────
        st.markdown("##### Tendencia de volumen — últimas 8 semanas")
        df_vol8 = pd.read_sql_query(
            """SELECT strftime('%Y-W%W', fecha) as semana, SUM(peso*reps) as volumen
               FROM entreno WHERE fecha >= DATE('now','-56 days')
               GROUP BY semana ORDER BY semana""", conn
        )
        if not df_vol8.empty:
            chart_v8 = alt.Chart(df_vol8).mark_area(
                opacity=0.25, color="#3b82f6",
                line={"color":"#3b82f6","strokeWidth":2},
                point=alt.OverlayMarkDef(color="#3b82f6", size=60)
            ).encode(
                x=alt.X("semana:O", title="Semana", axis=alt.Axis(labelAngle=-30)),
                y=alt.Y("volumen:Q", title="lb × reps", scale=alt.Scale(zero=True)),
                tooltip=[alt.Tooltip("semana:O"), alt.Tooltip("volumen:Q", format=",.0f")]
            ).properties(height=220)
            st.altair_chart(chart_v8, use_container_width=True)

        # ── E. Peso corporal vs Volumen ───────────────────────
        df_pc = pd.read_sql_query("SELECT DATE(fecha) as dia, peso FROM peso_corporal ORDER BY fecha", conn)
        df_vd = pd.read_sql_query(
            "SELECT DATE(fecha) as dia, SUM(peso*reps) as vol FROM entreno GROUP BY dia ORDER BY dia", conn
        )
        if not df_pc.empty and not df_vd.empty:
            st.divider()
            st.markdown("##### Peso corporal vs Volumen de entrenamiento")
            df_pc['dia'] = pd.to_datetime(df_pc['dia'])
            df_vd['dia'] = pd.to_datetime(df_vd['dia'])
            base_p = alt.Chart(df_pc).encode(x=alt.X("dia:T", axis=alt.Axis(format="%d/%m")))
            base_v = alt.Chart(df_vd).encode(x=alt.X("dia:T", axis=alt.Axis(format="%d/%m")))
            linea  = base_p.mark_line(color="#ef4444", strokeWidth=2,
                                      point=alt.OverlayMarkDef(color="#ef4444",size=50)
                     ).encode(y=alt.Y("peso:Q", title="Peso corporal (lb)", scale=alt.Scale(zero=False)),
                               tooltip=[alt.Tooltip("dia:T", format="%d/%m/%Y"), alt.Tooltip("peso:Q", format=".1f")])
            barras = base_v.mark_bar(color="#3b82f6", opacity=0.4,
                                     cornerRadiusTopLeft=3, cornerRadiusTopRight=3
                     ).encode(y=alt.Y("vol:Q", title="Volumen"),
                               tooltip=[alt.Tooltip("dia:T", format="%d/%m/%Y"), alt.Tooltip("vol:Q", format=",.0f")])
            st.altair_chart(alt.layer(barras, linea).resolve_scale(y="independent").properties(height=260),
                            use_container_width=True)
            st.caption("🔴 Línea = peso corporal  |  🔵 Barras = volumen")

# ══════════════════════════════════════════════════════════════════
# TAB 3 — CALENDARIO
# ══════════════════════════════════════════════════════════════════
with tab_calendario:
    df_dias = pd.read_sql_query(
        "SELECT DATE(inicio) as dia, nombre_rutina FROM sesiones WHERE fin IS NOT NULL ORDER BY dia",
        conn
    )
    dias_entrenados = {}
    if not df_dias.empty:
        for _, r in df_dias.iterrows():
            try:
                d = datetime.strptime(r['dia'], "%Y-%m-%d").date()
                dias_entrenados[d] = dias_entrenados.get(d, r['nombre_rutina'])
            except Exception:
                pass

    if "cal_mes"  not in st.session_state: st.session_state.cal_mes  = hoy.month
    if "cal_anio" not in st.session_state: st.session_state.cal_anio = hoy.year

    cp, cm, cn = st.columns([1, 4, 1])
    if cp.button("◀", use_container_width=True):
        if st.session_state.cal_mes == 1:
            st.session_state.cal_mes = 12; st.session_state.cal_anio -= 1
        else:
            st.session_state.cal_mes -= 1
        st.rerun()
    if cn.button("▶", use_container_width=True):
        if st.session_state.cal_mes == 12:
            st.session_state.cal_mes = 1; st.session_state.cal_anio += 1
        else:
            st.session_state.cal_mes += 1
        st.rerun()

    meses_es = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
    cm.markdown(f"<h3 style='text-align:center;margin:0'>{meses_es[st.session_state.cal_mes-1]} {st.session_state.cal_anio}</h3>",
                unsafe_allow_html=True)

    cal_grid = calendar.monthcalendar(st.session_state.cal_anio, st.session_state.cal_mes)
    dias_s   = ["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"]

    html = """<style>
    .cal{display:grid;grid-template-columns:repeat(7,1fr);gap:5px;margin-top:12px}
    .ch{text-align:center;font-size:12px;font-weight:700;color:#555;padding:4px}
    .cd{text-align:center;padding:10px 4px;border-radius:10px;font-size:14px;background:#1a1a1a;color:#bbb;min-height:42px}
    .cd.ent{background:#166534;color:#fff;font-weight:700}
    .cd.hoy{outline:2px solid #22c55e;outline-offset:1px}
    .cd.vacio{background:transparent}
    </style><div class='cal'>"""
    for d in dias_s: html += f"<div class='ch'>{d}</div>"
    for sem in cal_grid:
        for dn in sem:
            if dn == 0:
                html += "<div class='cd vacio'></div>"
            else:
                d_obj  = date(st.session_state.cal_anio, st.session_state.cal_mes, dn)
                cls    = "cd"
                title  = ""
                if d_obj in dias_entrenados: cls += " ent"; title = dias_entrenados[d_obj]
                if d_obj == hoy:             cls += " hoy"
                html += f"<div class='{cls}' title='{title}'>{dn}</div>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

    mes_dias = [d for d in dias_entrenados if d.month == st.session_state.cal_mes and d.year == st.session_state.cal_anio]
    if mes_dias:
        st.caption(f"✅ {len(mes_dias)} días entrenados este mes")
        for d in sorted(mes_dias, reverse=True)[:5]:
            st.caption(f"📅 {d.strftime('%d/%m')} — {dias_entrenados[d]}")

# ══════════════════════════════════════════════════════════════════
# TAB 4 — RECORDS PERSONALES
# ══════════════════════════════════════════════════════════════════
with tab_prs:
    st.subheader("🏆 Records Personales")

    df_prs = pd.read_sql_query(
        """SELECT ejercicio,
                  MAX(peso)        as max_peso,
                  MAX(reps)        as max_reps,
                  MAX(peso*reps)   as max_vol,
                  COUNT(*)         as total_series,
                  DATE(MAX(fecha)) as ultima_vez
           FROM entreno
           GROUP BY ejercicio
           ORDER BY max_peso DESC
           LIMIT 30""", conn
    )

    if df_prs.empty:
        st.info("Completa algunos entrenamientos para ver tus records aquí.")
    else:
        # Filtro rápido
        buscar = st.text_input("🔍 Buscar ejercicio", placeholder="Ej: press, curl, squat...")
        if buscar:
            df_prs = df_prs[df_prs['ejercicio'].str.lower().str.contains(buscar.lower())]

        df_prs.columns = ["Ejercicio","PR Peso (lb)","PR Reps","PR Volumen","Total Series","Última vez"]
        df_prs["PR Peso (lb)"]  = df_prs["PR Peso (lb)"].round(1)
        df_prs["PR Volumen"]    = df_prs["PR Volumen"].round(0).astype(int)
        st.dataframe(df_prs, use_container_width=True, hide_index=True)

        # Gráfica de top 10 por PR de peso
        st.subheader("Top 10 ejercicios por PR de peso")
        top10 = pd.read_sql_query(
            "SELECT ejercicio, MAX(peso) as max_peso FROM entreno GROUP BY ejercicio ORDER BY max_peso DESC LIMIT 10",
            conn
        )
        if not top10.empty:
            c10 = alt.Chart(top10).mark_bar(
                color="#f59e0b", cornerRadiusTopLeft=4, cornerRadiusTopRight=4
            ).encode(
                x=alt.X("max_peso:Q", title="lb"),
                y=alt.Y("ejercicio:N", sort="-x", title=None),
                tooltip=["ejercicio", alt.Tooltip("max_peso:Q", format=".1f", title="PR lb")]
            ).properties(height=280)
            st.altair_chart(c10, use_container_width=True)