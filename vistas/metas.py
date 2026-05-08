import streamlit as st
import sqlite3
import pandas as pd
import altair as alt
from datetime import datetime, date, timedelta

# ─────────────────────────────────────────────────────────────
# NAV
# ─────────────────────────────────────────────────────────────
from vistas.components.bottom_nav import inject_bottom_nav

inject_bottom_nav(active="metas")

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Metas",
    page_icon="🎯",
    layout="wide"
)

# ─────────────────────────────────────────────────────────────
# DB
# ─────────────────────────────────────────────────────────────
conn = sqlite3.connect("gym_data.db", check_same_thread=False)
c = conn.cursor()

# ─────────────────────────────────────────────────────────────
# CSS GLOBAL
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');

/* APP Y FONDO */
.stApp {
    background:#0f0f0f !important;
    font-family:'DM Sans',sans-serif !important;
    color:#f5f5f5 !important;
}

/* ELIMINAR ESPACIO SUPERIOR (IGUAL QUE EN STATS) */
.stAppViewMain > div > div > div {
    padding-top: 0px !important;
}

.block-container {
    padding-top: 0.5rem !important;
    padding-bottom: 10rem !important;
    max-width: 480px !important; /* Mantenemos el ancho móvil */
}

header[data-testid="stHeader"], div[data-testid="stToolbar"] { display:none !important; }

            
/* BOTÓN REGRESAR PEGADO ARRIBA */
div[data-testid="stVerticalBlock"] > div:first-child {
    margin-top: -10px !important;
}


            

/* HERO CARD */
.top-header {
    background: linear-gradient(135deg, rgba(230,57,70,0.1), rgba(22,22,22,1));
    border: 1px solid #262626;
    border-radius: 24px;
    padding: 24px;
    margin-bottom: 24px;
}

.top-kicker {
    color: #e63946;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-bottom: 8px;
}

.top-title {
    font-size: 30px;
    font-weight: 800;
    letter-spacing: -0.03em;
    color: white;
}

/* TABS SIMÉTRICOS (IGUAL QUE EN STATS) */
.stTabs [data-baseweb="tab-list"] {
    display: flex !important;
    width: 100% !important;
    gap: 8px !important;
    background: transparent !important;
}

.stTabs [data-baseweb="tab"] {
    flex: 1 !important;
    justify-content: center !important;
    background: #171717 !important;
    border-radius: 12px !important;
    color: #777 !important;
    padding: 10px 0px !important;
    border: none !important;
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg,#ef4444,#dc2626) !important;
    color: white !important;
}

/* CARDS DE METAS */
.glass-card {
    background: #161616;
    border: 1px solid #262626;
    border-radius: 22px;
    padding: 20px;
    margin-bottom: 16px;
}

/* INPUTS Y SELECTORS */
.stTextInput input, .stNumberInput input, .stDateInput input, div[data-baseweb="select"] {
    background: #1a1a1a !important;
    border: 1px solid #262626 !important;
    border-radius: 14px !important;
    color: white !important;
}

.stProgress > div > div > div {
    background: #e63946 !important;
}

/* MÉTRICAS */
div[data-testid="stMetric"] {
    background: #1a1a1a !important;
    border: 1px solid #262626 !important;
    border-radius: 16px !important;
    padding: 12px !important;
}
            

/* Estilo para el texto de días restantes */
.dias-label {
    color: #888;
    font-size: 14px;
    font-weight: 500;
    margin-bottom: 8px;
}

.dias-valor {
    color: #e63946; /* Rojo para resaltar los días */
    font-weight: 700;
}

/* Contenedor de métricas en línea */
.metricas-inline {
    display: flex;
    justify-content: space-between;
    margin-top: 12px;
    margin-bottom: 12px;
}

.metrica-item {
    font-size: 14px;
    color: #aaa;
}

.metrica-item strong {
    color: white;
    font-size: 15px;
}

/* Separador sutil */
.separador-meta {
    border: 0;
    border-top: 1px solid #262626;
    margin: 20px 0;
}
            
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# BOTÓN REGRESAR
# ─────────────────────────────────────────────────────────────
col_back, _ = st.columns([1, 5])

with col_back:
    if st.button("← Regresar", use_container_width=False):
        st.switch_page("vistas/inicio.py")

# ─────────────────────────────────────────────────────────────
# HERO
# ─────────────────────────────────────────────────────────────
st.markdown("""
<div class="top-header">

<div class="top-kicker">
        PROGRESO · OBJETIVOS · DISCIPLINA
</div>

<div class="top-title">
        🎯 Mis Metas
</div>

<div class="top-sub">
        Visualiza tus objetivos, mide tu progreso y mantén un seguimiento
        real de tu evolución en el gimnasio.
</div>

</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# TABLA
# ─────────────────────────────────────────────────────────────
c.execute("""
CREATE TABLE IF NOT EXISTS metas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ejercicio TEXT NOT NULL,
    tipo TEXT NOT NULL,
    valor_objetivo REAL NOT NULL,
    fecha_limite DATE NOT NULL,
    fecha_creacion DATE DEFAULT (DATE('now')),
    completada INTEGER DEFAULT 0
)
""")

conn.commit()

# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
def valor_actual(ejercicio, tipo):

    if tipo == "peso":
        row = c.execute(
            "SELECT MAX(peso) FROM entreno WHERE ejercicio=?",
            (ejercicio,)
        ).fetchone()

    elif tipo == "reps":
        row = c.execute(
            "SELECT MAX(reps) FROM entreno WHERE ejercicio=?",
            (ejercicio,)
        ).fetchone()

    else:
        row = c.execute(
            "SELECT MAX(peso*reps) FROM entreno WHERE ejercicio=?",
            (ejercicio,)
        ).fetchone()

    return float(row[0]) if row and row[0] else 0.0


def etiqueta_tipo(tipo):
    return {
        "peso": "Peso máximo",
        "reps": "Repeticiones",
        "volumen": "Volumen"
    }.get(tipo, tipo)

# ─────────────────────────────────────────────────────────────
# EJERCICIOS
# ─────────────────────────────────────────────────────────────
ejercicios = [
    r[0] for r in c.execute(
        "SELECT DISTINCT ejercicio FROM entreno ORDER BY ejercicio"
    ).fetchall()
]

# ─────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs([
    "Activas",
    "Nueva Meta",
    "Completada"
])

# ─────────────────────────────────────────────────────────────
# ACTIVAS
# ─────────────────────────────────────────────────────────────
with tab1:

    metas = c.execute("""
        SELECT id, ejercicio, tipo, valor_objetivo,
               fecha_limite, fecha_creacion
        FROM metas
        WHERE completada=0
        ORDER BY fecha_limite ASC
    """).fetchall()

    if not metas:
        st.info("No tienes metas activas todavía.")

    else:

        for meta in metas:
            mid, ejercicio, tipo, objetivo, fecha_lim, fecha_cre = meta
            actual = valor_actual(ejercicio, tipo)
            
            progreso = min(100, int((actual / objetivo) * 100)) if objetivo > 0 else 0
            dias_rest = (datetime.strptime(fecha_lim, "%Y-%m-%d").date() - date.today()).days

            # --- TODO EL CONTENIDO EN UN SOLO MARKDOWN ---
            st.markdown(f"""
            <div class="glass-card">
                <div style="color:#666; font-size:11px; font-weight:700; letter-spacing:0.12em; text-transform:uppercase;">
                    {etiqueta_tipo(tipo)}
                </div>
                <div style="font-size:24px; font-weight:800; color:white; margin-bottom:8px;">
                    {ejercicio}
                </div>
                <div class="dias-label">
                    Días restantes: <span class="dias-valor">{max(dias_rest, 0)}</span>
                </div>
                </div>
            """, unsafe_allow_html=True)

            # La barra de progreso de Streamlit (que no se puede meter en el HTML de arriba)
            st.progress(progreso / 100)

            # Métricas y botones alineados
            st.markdown(f"""
            <div class="metricas-inline">
                <div class="metrica-item">Actual: <strong>{actual:.1f}</strong></div>
                <div class="metrica-item">Objetivo: <strong>{objetivo:.1f}</strong></div>
                <div class="metrica-item">Progreso: <strong>{progreso}%</strong></div>
            </div>
            """, unsafe_allow_html=True)

            # Botones
            c1, c2 = st.columns(2)
            with c1:
                if progreso >= 100:
                    st.button("🏆 Completar", key=f"done_{mid}", use_container_width=True, type="primary")
            with c2:
                st.button("🗑️ Eliminar", key=f"del_{mid}", use_container_width=True, type="secondary")
            
            st.markdown("<hr class='separador-meta'>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# NUEVA META
# ─────────────────────────────────────────────────────────────
with tab2:

    st.markdown(
        "<div class='glass-card'>",
        unsafe_allow_html=True
    )

    st.subheader("Crear nueva meta")

    if not ejercicios:

        st.warning(
            "Necesitas registrar entrenamientos primero."
        )

    else:

        busq = st.text_input(
            "Buscar ejercicio",
            placeholder="Press banca..."
        )

        filtrados = [
            e for e in ejercicios
            if busq.lower() in e.lower()
        ] if busq else ejercicios

        ejercicio = st.selectbox(
            "Ejercicio",
            filtrados
        )

        tipo = st.radio(
            "Tipo",
            ["peso", "reps", "volumen"],
            horizontal=True,
            format_func=etiqueta_tipo
        )

        actual = valor_actual(ejercicio, tipo)

        st.caption(
            f"Valor actual: {actual:.1f}"
        )

        sugerido = actual * 1.10 if actual > 0 else 0.0

        objetivo = st.number_input(
            "Objetivo",
            min_value=0.0,
            value=float(round(sugerido, 1)),
            step=1.0
        )

        fecha = st.date_input(
            "Fecha límite",
            min_value=date.today() + timedelta(days=1),
            value=date.today() + timedelta(days=90)
        )

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button(
            "🎯 Crear Meta",
            use_container_width=True,
            type="primary"
        ):

            c.execute("""
                INSERT INTO metas (
                    ejercicio,
                    tipo,
                    valor_objetivo,
                    fecha_limite,
                    fecha_creacion
                )
                VALUES (?,?,?,?,?)
            """, (
                ejercicio,
                tipo,
                objetivo,
                fecha.isoformat(),
                date.today().isoformat()
            ))

            conn.commit()

            st.toast("🎯 Meta creada")
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# COMPLETADAS
# ─────────────────────────────────────────────────────────────
with tab3:

    done = c.execute("""
        SELECT ejercicio, tipo, valor_objetivo
        FROM metas
        WHERE completada=1
        ORDER BY id DESC
    """).fetchall()

    if not done:

        st.info("Todavía no completas metas.")

    else:

        st.success(
            f"🏆 Has completado {len(done)} metas"
        )

        for ej, tipo, val in done:

            st.markdown(f"""
            <div class='glass-card'>

                <div style="
                    color:#666;
                    font-size:11px;
                    font-weight:700;
                    letter-spacing:0.12em;
                    text-transform:uppercase;
                ">
                    {etiqueta_tipo(tipo)}
                </div>

                <div style="
                    font-size:24px;
                    font-weight:800;
                    margin-top:6px;
                    color:white;
                ">
                    ✅ {ej}
                </div>

                <div style="
                    color:#9ca3af;
                    margin-top:8px;
                    font-size:15px;
                ">
                    Objetivo alcanzado:
                    <strong style="color:white">
                        {val:.1f}
                    </strong>
                </div>

            </div>
            """, unsafe_allow_html=True)