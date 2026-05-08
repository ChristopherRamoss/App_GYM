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

/* APP */
.stApp,
section[data-testid="stMain"]{
    background:#0f0f0f !important;
    font-family:'DM Sans',sans-serif !important;
    color:#f5f5f5 !important;
}

/* Container */
.block-container{
    padding-top:1.5rem !important;
    padding-bottom:4rem !important;
    max-width:1400px;
}

/* Header */
header[data-testid="stHeader"]{
    background:#0f0f0f !important;
    border-bottom:1px solid #1e1e1e !important;
}

div[data-testid="stToolbar"]{
    display:none !important;
}

div[data-testid="stDecoration"]{
    display:none !important;
}

/* Sidebar */
section[data-testid="stSidebar"]{
    background:#141414 !important;
    border-right:1px solid #1f1f1f !important;
}

/* Texto */
h1,h2,h3,h4,h5,h6,p,span,label{
    font-family:'DM Sans',sans-serif !important;
    color:#f5f5f5 !important;
}

/* HERO */
.top-header{
    background:
        linear-gradient(
            135deg,
            rgba(230,57,70,0.15),
            rgba(17,17,17,0.85)
        );
    border:1px solid rgba(255,255,255,0.06);
    border-radius:24px;
    padding:28px;
    margin-bottom:24px;
}

.top-kicker{
    color:#666;
    font-size:12px;
    font-weight:700;
    letter-spacing:0.14em;
    text-transform:uppercase;
}

.top-title{
    color:white;
    font-size:36px;
    font-weight:800;
    letter-spacing:-0.04em;
    margin-top:10px;
}

.top-sub{
    color:#888;
    font-size:14px;
    margin-top:8px;
    line-height:1.6;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"]{
    gap:10px;
    margin-bottom:18px;
}

.stTabs [data-baseweb="tab"]{
    background:#171717 !important;
    border-radius:14px;
    padding:10px 18px;
    color:#777 !important;
    font-weight:600;
}

.stTabs [aria-selected="true"]{
    background:linear-gradient(135deg,#ef4444,#dc2626) !important;
    color:white !important;
}

/* Inputs */
.stTextInput input,
.stNumberInput input,
.stDateInput input,
.stSelectbox div[data-baseweb="select"]{
    background:#1a1a1a !important;
    border:1px solid #242424 !important;
    color:white !important;
    border-radius:14px !important;
}

/* Radio */
div[role="radiogroup"] label{
    background:#1a1a1a !important;
    border:1px solid #242424 !important;
    border-radius:12px !important;
    padding:10px 16px !important;
}

/* Buttons */
div[data-testid="stButton"] > button{
    border-radius:14px !important;
    font-weight:700 !important;
    transition:0.2s ease !important;
    border:none !important;
}

/* Primario */
div[data-testid="stButton"] > button[kind="primary"]{
    background:linear-gradient(135deg,#ef4444,#dc2626) !important;
    color:white !important;
}

/* Secundario */
div[data-testid="stButton"] > button[kind="secondary"]{
    background:#1a1a1a !important;
    border:1px solid #2a2a2a !important;
    color:#aaa !important;
}

/* Hover */
div[data-testid="stButton"] > button:hover{
    transform:translateY(-1px);
    filter:brightness(1.05);
}

/* Cards */
.glass-card{
    background:#1a1a1a;
    border:1px solid #242424;
    border-radius:22px;
    padding:22px;
    margin-bottom:18px;
}

/* Metrics */
div[data-testid="stMetric"]{
    background:#1a1a1a !important;
    border:1px solid #242424 !important;
    border-radius:18px !important;
    padding:18px !important;
}

div[data-testid="stMetricValue"]{
    color:white !important;
    font-weight:700 !important;
}

div[data-testid="stMetricLabel"]{
    color:#666 !important;
}

/* Progress */
.stProgress > div > div{
    background:#dc2626 !important;
    border-radius:999px !important;
    overflow:hidden;
}

.stProgress > div > div > div{
    background:linear-gradient(90deg,#333333,#333333) !important;
    border-radius:999px !important;
}

/* Alerts */
div[data-testid="stAlert"]{
    border-radius:16px !important;
}

/* Scroll */
::-webkit-scrollbar{
    width:10px;
}

::-webkit-scrollbar-thumb{
    background:#2b2b2b;
    border-radius:20px;
}

/* Footer */
footer{
    display:none !important;
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

            progreso = min(
                100,
                int((actual / objetivo) * 100)
            ) if objetivo > 0 else 0

            dias_rest = (
                datetime.strptime(fecha_lim, "%Y-%m-%d").date()
                - date.today()
            ).days

            with st.container(border=False):

                st.markdown(
                    "<div class='glass-card'>",
                    unsafe_allow_html=True
                )

                a, b = st.columns([4, 1])

                with a:
                    st.markdown(
                        f"""
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
                            font-size:28px;
                            font-weight:800;
                            margin-top:6px;
                            color:white;
                        ">
                            {ejercicio}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                with b:
                    st.metric(
                        "Días",
                        max(dias_rest, 0)
                    )

                st.progress(progreso / 100)

                c1, c2, c3 = st.columns(3)

                c1.metric(
                    "Actual",
                    f"{actual:.1f}"
                )

                c2.metric(
                    "Objetivo",
                    f"{objetivo:.1f}"
                )

                c3.metric(
                    "Progreso",
                    f"{progreso}%"
                )

                # Gráfico
                df = pd.read_sql_query("""
                    SELECT DATE(fecha) as dia,
                    MAX(
                        CASE
                            WHEN ?='peso' THEN peso
                            WHEN ?='reps' THEN reps
                            ELSE peso*reps
                        END
                    ) as val
                    FROM entreno
                    WHERE ejercicio=?
                    GROUP BY dia
                    ORDER BY dia
                """, conn, params=(tipo, tipo, ejercicio))

                if len(df) > 1:

                    df["dia"] = pd.to_datetime(df["dia"])

                    chart = alt.Chart(df).mark_line(
                        strokeWidth=3,
                        color="#ef4444"
                    ).encode(
                        x=alt.X("dia:T", title=None),
                        y=alt.Y("val:Q", title=None),
                        tooltip=["dia:T", "val:Q"]
                    ).properties(
                        height=140
                    )

                    st.altair_chart(
                        chart,
                        use_container_width=True
                    )

                aa, bb = st.columns(2)

                if progreso >= 100:
                    if aa.button(
                        "🏆 Completar",
                        key=f"done_{mid}",
                        use_container_width=True,
                        type="primary"
                    ):
                        c.execute(
                            "UPDATE metas SET completada=1 WHERE id=?",
                            (mid,)
                        )

                        conn.commit()

                        st.toast("🎉 Meta completada")
                        st.rerun()

                if bb.button(
                    "🗑️ Eliminar",
                    key=f"del_{mid}",
                    use_container_width=True
                ):
                    c.execute(
                        "DELETE FROM metas WHERE id=?",
                        (mid,)
                    )

                    conn.commit()

                    st.toast("Meta eliminada")
                    st.rerun()

                st.markdown("</div>", unsafe_allow_html=True)

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