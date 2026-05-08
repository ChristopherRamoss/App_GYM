import streamlit as st
import sqlite3
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
import streamlit.components.v1 as components
from vistas.components.bottom_nav import inject_bottom_nav

# ── CONFIGURACIÓN Y DATOS ──────────────────────────────────────────
conn = sqlite3.connect("gym_data.db", check_same_thread=False)
c    = conn.cursor()

# Inyectamos la navegación inferior con el estado activo en estadísticas
inject_bottom_nav(active="stats")

# ── CSS GLOBAL (Sincronizado con cuerpo.py) ───────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');

.stApp {
    background:#0f0f0f !important;
    font-family:'DM Sans',sans-serif !important;
    color:#f5f5f5 !important;
}

.block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 10rem !important;
    max-width: 480px !important;
}

header[data-testid="stHeader"], div[data-testid="stToolbar"] { display:none !important; }

/* --- DISEÑO DE FILTROS RECTANGULAR FULL-WIDTH --- */
div[role="radiogroup"] {
    display: flex;
    flex-direction: column;
    gap: 0px !important;
    background: #161616 !important;
    padding: 0px !important;
    width: 100vw !important;
    margin-left: calc(-50vw + 50%) !important;
    margin-right: calc(-50vw + 50%) !important;
    border-top: 1px solid #262626 !important;
    border-bottom: 1px solid #262626 !important;
}

div[role="radiogroup"] label {
    padding:4px 24px !important;
    width: 100% !important;
    border-bottom: 1px solid #262626 !important;
}

div[role="radiogroup"] label:last-child { border-bottom: none !important; }

div[role="radiogroup"] label:has(input:checked) {
    background: rgba(230, 57, 70, 0.1) !important;
}

div[role="radiogroup"] label:has(input:checked) p {
    color: #e63946 !important;
    font-weight: 600 !important;
}

/* Tabs personalizadas */
.stTabs [data-baseweb="tab-list"] { display: flex !important; width: 100% !important; gap: 8px !important; }
.stTabs [data-baseweb="tab"] {
    flex: 1 !important;
    justify-content: center !important;
    background: #171717 !important;
    border-radius: 12px;
    color: #777 !important;
    padding: 10px 0px !important;
}
.stTabs [aria-selected="true"] { 
    background: linear-gradient(135deg,#ef4444,#dc2626) !important; 
    color: white !important; 
}

/* Dataframe */
[data-testid="stDataFrame"] { background: #1a1a1a; border: 1px solid #242424; border-radius: 20px; }

/* Botón secundario (Back) */
div[data-testid="stButton"] > button[kind="secondary"] {
    background: #1a1a1a !important;
    border: 1px solid #262626 !important;
    color: #eee !important;
    border-radius: 12px !important;
}

/* Input de búsqueda */
.stTextInput input {
    background: #161616 !important;
    border: 1px solid #262626 !important;
    border-radius: 12px !important;
    color: white !important;
}
</style>
""", unsafe_allow_html=True)

# ── BOTÓN VOLVER E INICIO ──────────────────────────────────────────
if st.button("← Inicio", type="secondary"):
    st.switch_page("vistas/inicio.py")

st.markdown(f"""
<div style="padding: 10px 0 20px;">
    <p style="margin:0; font-size:12px; color:#555; font-weight:600; text-transform:uppercase; letter-spacing:0.12em;">Métricas de Rendimiento individuales</p>
    <h1 style="margin:6px 0 0; font-size:40px; font-weight:700; color:#fff; letter-spacing:-0.02em; line-height:1.2;">Mi <span style="color:#e63946;">Progreso</span></h1>
</div>
""", unsafe_allow_html=True)

# ── LOGICA DE DATOS ───────────────────────────────────────────────
ejercicios_con_datos = c.execute(
    "SELECT ejercicio, COUNT(*) as registros FROM entreno GROUP BY ejercicio ORDER BY registros DESC"
).fetchall()

if not ejercicios_con_datos:
    st.info("No hay datos registrados aún.")
    st.stop()

# ── SELECTOR DE EJERCICIO ─────────────────────────────────────────
# ── SELECTOR DE EJERCICIO ─────────────────────────────────────────
st.markdown('<p style="margin:0 0 10px; font-size:12px; font-weight:700; color:#555; text-transform:uppercase; letter-spacing:0.1em;">Seleccionar Ejercicio</p>', unsafe_allow_html=True)

# Obtenemos la lista completa de ejercicios
nombres_ej = [r[0] for r in ejercicios_con_datos]

# Eliminamos el st.text_input y filtramos directamente con el selectbox
ej_sel = st.selectbox(
    "Ejercicio", 
    nombres_ej, 
    label_visibility="collapsed",
    key="selector_ejercicio_unico"
)

# ── SELECTOR DE RANGO (Estilo cuerpo.py) ──────────────────────────
st.markdown('<p style="margin:20px 0 10px; font-size:12px; font-weight:700; color:#555; text-transform:uppercase; letter-spacing:0.1em;">Rango de Tiempo</p>', unsafe_allow_html=True)
rango = st.radio(
    "FiltroRango",
    ["1 mes", "3 meses", "6 meses", "Todo"],
    index=1,
    label_visibility="collapsed"
)

dias_map = {"1 mes": 30, "3 meses": 90, "6 meses": 180, "Todo": 9999}
desde = (datetime.now() - timedelta(days=dias_map[rango])).isoformat()

# ── PROCESAMIENTO DE DATOS ────────────────────────────────────────
df = pd.read_sql_query(
    "SELECT peso, reps, fecha, (peso * reps) as volumen FROM entreno WHERE ejercicio = ? AND fecha >= ? ORDER BY fecha ASC",
    conn, params=(ej_sel, desde)
)

if df.empty:
    st.info("Sin datos para este periodo.")
    st.stop()

df['fecha_dt'] = pd.to_datetime(df['fecha'])
df['dia'] = df['fecha_dt'].dt.date
pr_por_dia = df.groupby('dia').agg(max_peso=('peso', 'max'), max_vol=('volumen', 'max'), total_series=('peso', 'count')).reset_index()
pr_por_dia['dia_dt'] = pd.to_datetime(pr_por_dia['dia'])

# ── PESTAÑAS DE VISUALIZACIÓN ─────────────────────────────────────
t1, t2, t3 = st.tabs(["📊 Evolución", "📦 Volumen", "📋 Historial"])

with t1:
    st.markdown('<p style="margin:10px 0; font-size:13px; font-weight:700; color:#555; text-transform:uppercase;">Evolución del PR (lb)</p>', unsafe_allow_html=True)
    
    linea = alt.Chart(pr_por_dia).mark_line(color='#e63946', strokeWidth=3).encode(
        x=alt.X('dia_dt:T', title=None, axis=alt.Axis(format='%d/%m', labelAngle=-30, grid=False)),
        y=alt.Y('max_peso:Q', title=None, scale=alt.Scale(zero=False))
    )
    puntos = linea.mark_circle(color='#e63946', size=80).encode(
        tooltip=[alt.Tooltip('dia:T', title='Fecha'), alt.Tooltip('max_peso:Q', title='Peso Max')]
    )
    st.altair_chart((linea + puntos).properties(height=300), use_container_width=True)

with t2:
    st.markdown('<p style="margin:10px 0; font-size:13px; font-weight:700; color:#555; text-transform:uppercase;">Volumen por Sesión</p>', unsafe_allow_html=True)
    barras = alt.Chart(pr_por_dia).mark_bar(color='#262626', cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
        x=alt.X('dia_dt:T', title=None, axis=alt.Axis(format='%d/%m')),
        y=alt.Y('max_vol:Q', title=None),
        tooltip=['dia:T', 'max_vol:Q']
    ).configure_view(strokeOpacity=0)
    st.altair_chart(barras.properties(height=300), use_container_width=True)

with t3:
    st.markdown('<p style="margin:10px 0; font-size:13px; font-weight:700; color:#555; text-transform:uppercase;">Registros Completos</p>', unsafe_allow_html=True)
    df_show = df[['fecha', 'peso', 'reps', 'volumen']].copy()
    df_show['fecha'] = pd.to_datetime(df_show['fecha']).dt.strftime('%d/%m/%Y %H:%M')
    st.dataframe(df_show.iloc[::-1], use_container_width=True, hide_index=True)

# ── MÉTRICAS RÁPIDAS ──────────────────────────────────────────────
st.markdown("---")
m1, m2 = st.columns(2)
with m1:
    st.metric("PR Absoluto", f"{df['peso'].max()} lb")
with m2:
    total_vol = df['volumen'].sum()
    st.metric("Volumen Total", f"{int(total_vol)}")