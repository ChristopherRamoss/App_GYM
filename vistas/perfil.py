import streamlit as st
import sqlite3
import pandas as pd
import altair as alt
from datetime import datetime
from vistas.components.bottom_nav import inject_bottom_nav

# ─── CONFIG ──────────────────────────────────────────────────────
st.set_page_config(page_title="Perfil", page_icon="👤", layout="centered")

inject_bottom_nav(active="perfil")

# ─── CONEXIÓN ────────────────────────────────────────────────────
conn = sqlite3.connect("gym_data.db", check_same_thread=False)
c    = conn.cursor()

# ─── ASEGURAR TABLAS ─────────────────────────────────────────────
c.execute("""
CREATE TABLE IF NOT EXISTS perfil (
    id     INTEGER PRIMARY KEY,
    nombre TEXT DEFAULT 'Christopher',
    edad   INTEGER DEFAULT 25
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS peso_corporal (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    peso  REAL,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

c.execute("""
INSERT OR IGNORE INTO perfil (id, nombre, edad)
VALUES (1, 'Christopher', 25)
""")

conn.commit()

# ─── NAV ─────────────────────────────────────────────────────────
inject_bottom_nav(active="perfil")

# ─── CSS GLOBAL ──────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');

/* Fondo */
.stApp, section[data-testid="stMain"] {
    background: #0f0f0f !important;
    font-family: 'DM Sans', sans-serif !important;
}

/* Header */
header[data-testid="stHeader"] {
    background: #0f0f0f !important;
    border-bottom: 1px solid #1e1e1e !important;
}

div[data-testid="stToolbar"] {
    display: none !important;
}

div[data-testid="stDecoration"] {
    display: none !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #141414 !important;
    border-right: 1px solid #1e1e1e !important;
}

/* Texto */
h1, h2, h3, h4, h5, h6, p, span, label {
    font-family: 'DM Sans', sans-serif !important;
}

/* Inputs */
.stTextInput input,
.stNumberInput input {
    background: #1a1a1a !important;
    border: 1px solid #242424 !important;
    color: white !important;
    border-radius: 14px !important;
}

/* Selects */
.stSelectbox > div > div {
    background: #1a1a1a !important;
    border: 1px solid #242424 !important;
    border-radius: 14px !important;
}

/* Expander */
.streamlit-expanderHeader {
    background: #1a1a1a !important;
    border-radius: 14px !important;
}

/* Botones */
div[data-testid="stButton"] > button[kind="primary"] {
    background: #e63946 !important;
    border: none !important;
    border-radius: 14px !important;
    font-weight: 700 !important;
    color: white !important;
    padding: 14px 20px !important;
}

div[data-testid="stButton"] > button[kind="secondary"] {
    background: #1a1a1a !important;
    border: 1px solid #242424 !important;
    border-radius: 14px !important;
    color: #aaa !important;
}

/* Download button */
div[data-testid="stDownloadButton"] button {
    background: #1a1a1a !important;
    border: 1px solid #242424 !important;
    border-radius: 14px !important;
    color: #fff !important;
}

/* Métricas */
div[data-testid="stMetric"] {
    background: #1a1a1a !important;
    border: 1px solid #242424 !important;
    border-radius: 18px !important;
    padding: 18px !important;
}

div[data-testid="stMetricValue"] > div {
    font-size: 28px !important;
    font-weight: 700 !important;
    color: #fff !important;
}

div[data-testid="stMetricLabel"] > div {
    font-size: 11px !important;
    color: #666 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
}

/* Dataframe */
[data-testid="stDataFrame"] {
    border: 1px solid #242424 !important;
    border-radius: 16px !important;
    overflow: hidden !important;
}

/* Divider */
hr {
    border-color: #1e1e1e !important;
    margin: 24px 0 !important;
}

/* Footer */
footer {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)

# ─── CARGAR PERFIL ───────────────────────────────────────────────
perfil = c.execute(
    "SELECT nombre, edad FROM perfil WHERE id = 1"
).fetchone()

nombre_actual = perfil[0] if perfil else "Christopher"
edad_actual   = perfil[1] if perfil else 25

# ─── PESO MÁS RECIENTE ───────────────────────────────────────────
ultimo_peso_row = c.execute(
    "SELECT peso, fecha FROM peso_corporal ORDER BY fecha DESC LIMIT 1"
).fetchone()

peso_actual = ultimo_peso_row[0] if ultimo_peso_row else None

# ══════════════════════════════════════════════════════════════════
# HERO
# ══════════════════════════════════════════════════════════════════
st.markdown(f"""
<div style="padding: 28px 0 8px;">
<p style="margin:0; font-size:12px; color:#555; font-weight:600;
              text-transform:uppercase; letter-spacing:0.12em;">
        PERFIL
</p>

<h1 style="margin:6px 0 0; font-size:30px; font-weight:700;
               color:#fff; letter-spacing:-0.02em;">
        {nombre_actual} {edad_actual} años
</h1>

<p style="margin:8px 0 0; font-size:13px; color:#666;">
        Gestiona tu información y monitorea tu evolución física
</p>
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# MÉTRICAS
# ══════════════════════════════════════════════════════════════════
peso_display = f"{peso_actual:.1f} lb" if peso_actual else "—"

col1, col2, col3 = st.columns(3)

col1.metric("Peso actual", peso_display)
col2.metric("Edad", f"{edad_actual}")
col3.metric("Nivel", "Dios griego")

st.markdown("<div style='height:30px'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# EDITAR PERFIL
# ══════════════════════════════════════════════════════════════════
st.markdown("""
<p style="margin:0 0 14px; font-size:13px; font-weight:700; color:#555;
          text-transform:uppercase; letter-spacing:0.1em;">
    Configuración
</p>
""", unsafe_allow_html=True)

with st.container(border=True):

    st.markdown("""
    <p style="font-size:18px; font-weight:700; color:#fff; margin-bottom:20px;">
        Editar datos personales
    </p>
    """, unsafe_allow_html=True)

    nuevo_nombre = st.text_input(
        "Nombre",
        value=nombre_actual
    )

    nueva_edad = st.number_input(
        "Edad",
        min_value=10,
        max_value=100,
        value=int(edad_actual)
    )

    if st.button(
        "Guardar cambios",
        use_container_width=True,
        type="primary"
    ):
        c.execute(
            "UPDATE perfil SET nombre = ?, edad = ? WHERE id = 1",
            (nuevo_nombre, nueva_edad)
        )

        conn.commit()

        st.toast("✅ Perfil actualizado")
        st.rerun()

st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# REGISTRAR PESO
# ══════════════════════════════════════════════════════════════════
st.markdown("""
<p style="margin:0 0 14px; font-size:13px; font-weight:700; color:#555;
          text-transform:uppercase; letter-spacing:0.1em;">
    Registrar peso
</p>
""", unsafe_allow_html=True)

with st.container(border=True):

    st.markdown("""
    <p style="font-size:18px; font-weight:700; color:#fff; margin-bottom:16px;">
        Peso corporal de hoy
    </p>
    """, unsafe_allow_html=True)

    cp1, cp2 = st.columns([2, 1])

    nuevo_peso = cp1.number_input(
        "Peso corporal",
        min_value=50.0,
        max_value=500.0,
        value=float(peso_actual) if peso_actual else 150.0,
        step=0.5,
        label_visibility="collapsed"
    )

    if cp2.button(
        "Registrar",
        use_container_width=True,
        type="primary"
    ):
        c.execute(
            "INSERT INTO peso_corporal (peso) VALUES (?)",
            (nuevo_peso,)
        )

        conn.commit()

        st.toast(f"✅ {nuevo_peso:.1f} lb registradas")
        st.rerun()

st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# EVOLUCIÓN DE PESO
# ══════════════════════════════════════════════════════════════════
st.markdown("""
<p style="margin:0 0 14px; font-size:13px; font-weight:700; color:#555;
          text-transform:uppercase; letter-spacing:0.1em;">
    Evolución corporal
</p>
""", unsafe_allow_html=True)

df_peso = pd.read_sql_query(
    "SELECT peso, fecha FROM peso_corporal ORDER BY fecha ASC",
    conn
)

if df_peso.empty:

    st.markdown("""
    <div style="background:#1a1a1a; border:1px dashed #2a2a2a;
                border-radius:20px; padding:40px; text-align:center;">

        <p style="font-size:32px; margin:0;">⚖️</p>

        <p style="font-size:15px; font-weight:600; color:#aaa;
                  margin:12px 0 4px;">
            Sin registros de peso
        </p>

        <p style="font-size:13px; color:#555; margin:0;">
            Empieza registrando tu peso corporal
        </p>

    </div>
    """, unsafe_allow_html=True)

else:

    df_peso['fecha'] = pd.to_datetime(df_peso['fecha'])
    df_peso['fecha_str'] = df_peso['fecha'].dt.strftime('%d/%m/%Y')

    chart = alt.Chart(df_peso).mark_line(
        point=alt.OverlayMarkDef(size=70, filled=True),
        color="#e63946",
        strokeWidth=3
    ).encode(
        x=alt.X(
            'fecha:T',
            title=None,
            axis=alt.Axis(format='%d/%m')
        ),
        y=alt.Y(
            'peso:Q',
            title='Peso (lb)',
            scale=alt.Scale(zero=False)
        ),
        tooltip=[
            alt.Tooltip('fecha_str:N', title='Fecha'),
            alt.Tooltip('peso:Q', title='Peso', format='.1f')
        ]
    ).properties(
        height=320
    )

    st.altair_chart(chart, use_container_width=True)

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # RESUMEN
    if len(df_peso) >= 2:

        peso_inicial = df_peso['peso'].iloc[0]
        peso_actual  = df_peso['peso'].iloc[-1]
        diferencia   = peso_actual - peso_inicial

        r1, r2, r3 = st.columns(3)

        r1.metric("Inicial", f"{peso_inicial:.1f} lb")
        r2.metric("Actual",  f"{peso_actual:.1f} lb")
        r3.metric(
            "Cambio",
            f"{diferencia:+.1f} lb",
            delta_color="inverse" if diferencia > 0 else "normal"
        )

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # TABLA
    st.markdown("""
    <p style="font-size:18px; font-weight:700; color:#fff; margin-bottom:12px;">
        Historial
    </p>
    """, unsafe_allow_html=True)

    df_tabla = df_peso[['fecha_str', 'peso']].copy()

    df_tabla = df_tabla.rename(columns={
        'fecha_str': 'Fecha',
        'peso': 'Peso (lb)'
    })

    df_tabla['Cambio'] = df_tabla['Peso (lb)'].diff().round(1)

    def formato_cambio(val):
        if pd.isna(val):
            return "—"
        elif val > 0:
            return f"⬆️ +{val:.1f}"
        elif val < 0:
            return f"⬇️ {val:.1f}"
        return "➡️ 0.0"

    df_tabla['Cambio'] = df_tabla['Cambio'].apply(formato_cambio)

    df_tabla = df_tabla.iloc[::-1].reset_index(drop=True)

    st.dataframe(
        df_tabla,
        use_container_width=True,
        hide_index=True
    )

st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# EXPORTAR
# ══════════════════════════════════════════════════════════════════
st.markdown("""
<p style="margin:0 0 14px; font-size:13px; font-weight:700; color:#555;
          text-transform:uppercase; letter-spacing:0.1em;">
    Exportar datos
</p>
""", unsafe_allow_html=True)

df_historial = pd.read_sql_query(
    """
    SELECT ejercicio, peso, reps, fecha
    FROM entreno
    ORDER BY fecha DESC
    """,
    conn
)

with st.container(border=True):

    st.markdown("""
    <p style="font-size:18px; font-weight:700; color:#fff; margin-bottom:12px;">
        Historial de entrenamientos
    </p>
    """, unsafe_allow_html=True)

    if not df_historial.empty:

        csv = df_historial.to_csv(index=False).encode('utf-8')

        st.download_button(
            label="⬇️ Descargar CSV",
            data=csv,
            file_name=f"historial_gym_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )

    else:
        st.info("Aún no hay historial disponible.")