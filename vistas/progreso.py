import streamlit as st
import sqlite3
import pandas as pd
import altair as alt
from datetime import datetime, timedelta

conn = sqlite3.connect("gym_data.db", check_same_thread=False)
c    = conn.cursor()

st.title("📈 Mi Progreso")

# ── Obtener ejercicios con historial ──────────────────────────────
ejercicios_con_datos = c.execute(
    """SELECT ejercicio, COUNT(*) as registros, MAX(peso) as max_peso
       FROM entreno GROUP BY ejercicio ORDER BY registros DESC"""
).fetchall()

if not ejercicios_con_datos:
    st.info("Aún no tienes historial de entrenamientos. ¡Completa tu primer entreno para ver tu progreso aquí!")
    st.stop()

# ── Selector de ejercicio ─────────────────────────────────────────
nombres_ej = [r[0] for r in ejercicios_con_datos]

# Busqueda por texto para encontrar ejercicio rápido en móvil
busqueda = st.text_input(
    "Buscar ejercicio",
    placeholder="Escribe para filtrar...",
    label_visibility="collapsed",
)
if busqueda.strip():
    nombres_filtrados = [n for n in nombres_ej if busqueda.lower() in n.lower()]
else:
    nombres_filtrados = nombres_ej

if not nombres_filtrados:
    st.warning(f"No se encontró ningún ejercicio con '{busqueda}'")
    st.stop()

ej_sel = st.selectbox(
    "Ejercicio",
    nombres_filtrados,
    label_visibility="collapsed",
)

# ── Rango de tiempo ───────────────────────────────────────────────
rango = st.radio(
    "Rango",
    ["1 mes", "3 meses", "6 meses", "Todo"],
    horizontal=True,
    label_visibility="collapsed",
    index=1,
)
dias_map = {"1 mes": 30, "3 meses": 90, "6 meses": 180, "Todo": 9999}
dias     = dias_map[rango]
desde    = (datetime.now() - timedelta(days=dias)).isoformat()

# ── Cargar datos del ejercicio ────────────────────────────────────
df = pd.read_sql_query(
    """SELECT peso, reps, fecha,
              (peso * reps) as volumen
       FROM entreno
       WHERE ejercicio = ? AND fecha >= ?
       ORDER BY fecha ASC""",
    conn, params=(ej_sel, desde)
)

if df.empty:
    st.info(f"Sin datos de **{ej_sel}** en el período seleccionado.")
    st.stop()

df['fecha_dt']  = pd.to_datetime(df['fecha'])
df['fecha_str'] = df['fecha_dt'].dt.strftime('%d/%m/%Y')
df['dia']       = df['fecha_dt'].dt.date

# ── PR por día (máximo peso en cada sesión) ───────────────────────
pr_por_dia = df.groupby('dia').agg(
    max_peso=('peso', 'max'),
    max_vol=('volumen', 'max'),
    max_reps=('reps', 'max'),
    total_series=('peso', 'count'),
).reset_index()
pr_por_dia['dia_dt']  = pd.to_datetime(pr_por_dia['dia'])
pr_por_dia['dia_str'] = pr_por_dia['dia_dt'].dt.strftime('%d/%m')

# ── Métricas de cabecera ──────────────────────────────────────────
pr_absoluto   = df['peso'].max()
vol_maximo    = df['volumen'].max()
total_sesiones = pr_por_dia.shape[0]
primera_fecha = df['fecha_dt'].min().strftime('%d/%m/%Y')
ultimo_peso   = pr_por_dia['max_peso'].iloc[-1]
primer_peso   = pr_por_dia['max_peso'].iloc[0]
mejora        = ultimo_peso - primer_peso

col1, col2, col3, col4 = st.columns(4)
col1.metric("🏆 PR Absoluto",    f"{pr_absoluto:.1f} lb")
col2.metric("📦 Mejor volumen",  f"{vol_maximo:.0f}")
col3.metric("📅 Sesiones",       total_sesiones)
col4.metric(
    "📈 Mejora total",
    f"{mejora:+.1f} lb",
    delta=f"desde {primera_fecha}",
    delta_color="normal" if mejora >= 0 else "inverse",
)

st.divider()

# ══════════════════════════════════════════════════════════════════
# GRÁFICA 1 — Evolución del PR de peso
# ══════════════════════════════════════════════════════════════════
st.subheader("🏋️ Evolución del peso máximo")

base = alt.Chart(pr_por_dia).encode(
    x=alt.X('dia_dt:T', title=None, axis=alt.Axis(format='%d/%m', labelAngle=-30)),
)

linea_peso = base.mark_line(
    color='#3b82f6', strokeWidth=2.5
).encode(
    y=alt.Y('max_peso:Q', title='Peso (lb)', scale=alt.Scale(zero=False)),
    tooltip=[
        alt.Tooltip('dia_str:N',   title='Fecha'),
        alt.Tooltip('max_peso:Q',  title='Peso (lb)', format='.1f'),
        alt.Tooltip('total_series:Q', title='Series ese día'),
    ]
)

puntos = base.mark_circle(
    color='#3b82f6', size=70
).encode(
    y=alt.Y('max_peso:Q', scale=alt.Scale(zero=False)),
)

# Marcar el PR absoluto con un punto especial
df_pr_max = pr_por_dia[pr_por_dia['max_peso'] == pr_por_dia['max_peso'].max()].head(1)
punto_pr = alt.Chart(df_pr_max).mark_point(
    shape='triangle-up', size=150, color='#f59e0b', filled=True
).encode(
    x=alt.X('dia_dt:T'),
    y=alt.Y('max_peso:Q', scale=alt.Scale(zero=False)),
    tooltip=[alt.Tooltip('max_peso:Q', title='🏆 PR', format='.1f')]
)

st.altair_chart(
    (linea_peso + puntos + punto_pr).properties(height=260),
    use_container_width=True
)
st.caption("🔺 Triángulo = PR histórico en ese período")

# ══════════════════════════════════════════════════════════════════
# GRÁFICA 2 — Volumen por sesión
# ══════════════════════════════════════════════════════════════════
st.subheader("📦 Volumen por sesión")
st.caption("Volumen = suma de (peso × reps) en cada día")

vol_dia = df.groupby('dia').agg(
    vol_total=('volumen', 'sum')
).reset_index()
vol_dia['dia_dt']  = pd.to_datetime(vol_dia['dia'])
vol_dia['dia_str'] = vol_dia['dia_dt'].dt.strftime('%d/%m')

chart_vol = alt.Chart(vol_dia).mark_bar(
    color='#22c55e', cornerRadiusTopLeft=4, cornerRadiusTopRight=4
).encode(
    x=alt.X('dia_dt:T', title=None, axis=alt.Axis(format='%d/%m', labelAngle=-30)),
    y=alt.Y('vol_total:Q', title='Volumen (lb × reps)'),
    tooltip=[
        alt.Tooltip('dia_str:N',   title='Fecha'),
        alt.Tooltip('vol_total:Q', title='Volumen', format=',.0f'),
    ]
).properties(height=200)
st.altair_chart(chart_vol, use_container_width=True)

# ══════════════════════════════════════════════════════════════════
# GRÁFICA 3 — Distribución de reps al máximo peso
# ══════════════════════════════════════════════════════════════════
st.subheader("🔁 Reps al peso máximo del día")
st.caption("¿Cuántas reps lograste el día que más pesaste?")

chart_reps = alt.Chart(pr_por_dia).mark_line(
    color='#a855f7', strokeWidth=2,
    point=alt.OverlayMarkDef(color='#a855f7', size=55)
).encode(
    x=alt.X('dia_dt:T', title=None, axis=alt.Axis(format='%d/%m', labelAngle=-30)),
    y=alt.Y('max_reps:Q', title='Reps', scale=alt.Scale(zero=False)),
    tooltip=[
        alt.Tooltip('dia_str:N',  title='Fecha'),
        alt.Tooltip('max_reps:Q', title='Reps'),
    ]
).properties(height=180)
st.altair_chart(chart_reps, use_container_width=True)

# ══════════════════════════════════════════════════════════════════
# TABLA DE HISTORIAL COMPLETO
# ══════════════════════════════════════════════════════════════════
st.divider()
with st.expander("📋 Ver historial completo"):
    df_tabla = df[['fecha_str', 'peso', 'reps', 'volumen']].copy()
    df_tabla.columns = ['Fecha', 'Peso (lb)', 'Reps', 'Volumen']
    df_tabla['Peso (lb)'] = df_tabla['Peso (lb)'].round(1)
    df_tabla['Volumen']   = df_tabla['Volumen'].round(0).astype(int)
    df_tabla = df_tabla.iloc[::-1].reset_index(drop=True)
    st.dataframe(df_tabla, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════
# COMPARATIVA ENTRE EJERCICIOS
# ══════════════════════════════════════════════════════════════════
st.divider()
st.subheader("⚖️ Comparar con otro ejercicio")

otros = [n for n in nombres_ej if n != ej_sel]
if otros:
    ej_comp = st.selectbox("Comparar con:", otros, label_visibility="collapsed")

    df_comp = pd.read_sql_query(
        """SELECT dia, MAX(peso) as max_peso
           FROM (SELECT DATE(fecha) as dia, peso FROM entreno
                 WHERE ejercicio = ? AND fecha >= ?)
           GROUP BY dia ORDER BY dia""",
        conn, params=(ej_comp, desde)
    )

    if not df_comp.empty:
        df_comp['dia_dt'] = pd.to_datetime(df_comp['dia'])
        df_a = pr_por_dia[['dia_dt','max_peso']].copy()
        df_a['ejercicio'] = ej_sel
        df_b = df_comp[['dia_dt','max_peso']].copy()
        df_b['ejercicio'] = ej_comp

        df_ambos = pd.concat([df_a, df_b], ignore_index=True)

        chart_comp = alt.Chart(df_ambos).mark_line(
            strokeWidth=2, point=alt.OverlayMarkDef(size=50)
        ).encode(
            x=alt.X('dia_dt:T', title=None, axis=alt.Axis(format='%d/%m', labelAngle=-30)),
            y=alt.Y('max_peso:Q', title='Peso (lb)', scale=alt.Scale(zero=False)),
            color=alt.Color('ejercicio:N', legend=alt.Legend(title=None)),
            tooltip=['ejercicio:N',
                     alt.Tooltip('max_peso:Q', format='.1f', title='lb'),
                     alt.Tooltip('dia_dt:T',   format='%d/%m/%Y', title='Fecha')]
        ).properties(height=220)
        st.altair_chart(chart_comp, use_container_width=True)
    else:
        st.info(f"Sin datos de {ej_comp} en este período.")