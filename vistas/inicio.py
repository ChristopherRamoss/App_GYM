import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta, date
import hashlib
import sys, os
from vistas.components.bottom_nav import inject_bottom_nav

conn = sqlite3.connect("gym_data.db", check_same_thread=False)
c    = conn.cursor()
inject_bottom_nav(active="inicio")


# ── CSS global ────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');

/* Fondo y tipografía base */
.stApp, section[data-testid="stMain"] {
    background: #0f0f0f !important;
    font-family: 'DM Sans', sans-serif !important;
}

/* Header azul — eliminarlo */
header[data-testid="stHeader"] {
    background: #0f0f0f !important;
    border-bottom: 1px solid #1e1e1e !important;
}
div[data-testid="stToolbar"] { display: none !important; }
div[data-testid="stDecoration"] { display: none !important; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #141414 !important;
    border-right: 1px solid #1e1e1e !important;
}

/* Botones primarios */
div[data-testid="stButton"] > button[kind="primary"] {
    background: #e63946 !important;
    border: none !important;
    border-radius: 14px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 700 !important;
    font-size: 15px !important;
    padding: 14px 24px !important;
    color: #fff !important;
    letter-spacing: 0.01em !important;
}
div[data-testid="stButton"] > button[kind="secondary"] {
    background: #1e1e1e !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 12px !important;
    font-family: 'DM Sans', sans-serif !important;
    color: #aaa !important;
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

/* Divider */
hr { border-color: #1e1e1e !important; margin: 24px 0 !important; }

/* Footer */
footer { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ── Datos ─────────────────────────────────────────────────────────
perfil      = c.execute("SELECT nombre FROM perfil WHERE id=1").fetchone()
nombre      = perfil[0] if perfil else "Atleta"
hora        = datetime.now().hour
hoy         = date.today()
lunes       = hoy - timedelta(days=hoy.weekday())

saludo = "Buenos días" if hora < 12 else ("Buenas tardes" if hora < 19 else "Buenas noches")

total_ses   = c.execute("SELECT COUNT(*) FROM sesiones WHERE fin IS NOT NULL").fetchone()[0]
ses_semana  = c.execute("SELECT COUNT(*) FROM sesiones WHERE fin IS NOT NULL AND DATE(inicio)>=?", (lunes.isoformat(),)).fetchone()[0]
vol_semana  = c.execute("SELECT COALESCE(SUM(peso*reps),0) FROM entreno WHERE DATE(fecha)>=?", (lunes.isoformat(),)).fetchone()[0]
ult_peso    = c.execute("SELECT peso FROM peso_corporal ORDER BY fecha DESC LIMIT 1").fetchone()

# Racha
dias_ent = c.execute("SELECT DISTINCT DATE(inicio) FROM sesiones WHERE fin IS NOT NULL ORDER BY 1 DESC LIMIT 30").fetchall()
racha = 0
if dias_ent:
    check = hoy
    for (d_str,) in dias_ent:
        try:
            d = datetime.strptime(d_str, "%Y-%m-%d").date()
            if d == check or d == check - timedelta(days=1):
                racha += 1; check = d
            else:
                break
        except Exception:
            pass

frases = [
    "El único mal entrenamiento es el que no hiciste.",
]
frase = frases[int(hashlib.md5(hoy.isoformat().encode()).hexdigest(), 16) % len(frases)]

# ══════════════════════════════════════════════════════════════════
# HERO
# como se hace un salto de linea en un f-string con HTML? con <br> y usando unsafe_allow_html=True, pero sin meter lógica dentro del HTML para evitar problemas de renderizado o seguridad.
# ══════════════════════════════════════════════════════════════════
st.markdown(f"""
<div style="padding: 28px 0 8px;">
    <p style="margin:0; font-size:12px; color:#555; font-weight:600;
              text-transform:uppercase; letter-spacing:0.12em;">
        {hoy.strftime('%A %d de %B').capitalize()}
    </p>
    <h1 style="margin:6px 0 0; font-size:28px; font-weight:700; color:#fff;
               letter-spacing:-0.02em; line-height:1.2;">
        {saludo} <span style="color:#e63946;">{nombre}</span>
    </h1>
    <p style="margin:8px 0 0; font-size:13px; color:#555; font-style:italic;">
        "{frase}"
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ── CTA principal ─────────────────────────────────────────────────
if st.button("▶  Entrenar ahora", use_container_width=True, type="primary"):
    st.switch_page("vistas/mis_rutinas.py")

st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)

# ── 4 métricas ────────────────────────────────────────────────────
vol_display = f"{vol_semana/1000:.1f}k" if vol_semana > 999 else f"{vol_semana:.0f}"
peso_display = f"{ult_peso[0]:.0f} lb" if ult_peso else "—"
racha_display = f"{racha} 🔥" if racha > 0 else "0"

c1, c2, c3, c4 = st.columns(4)
c1.metric("Esta semana",   ses_semana)
c2.metric("Racha",         racha_display)
c3.metric("Volumen semanal",    vol_display)
c4.metric("Peso corporal",          peso_display)

st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

# ── Quick actions ────────────────────────────────────────────────
st.markdown("""
<p style="margin:0 0 14px; font-size:13px; font-weight:700; color:#555;
          text-transform:uppercase; letter-spacing:0.1em;">
    Acciones rápidas
</p>
""", unsafe_allow_html=True)

qa1, qa2, qa3, qa4 = st.columns(4)
with qa1:
    if st.button("**Nueva rutina**",  use_container_width=True, key="qa_rutina"):
        st.switch_page("vistas/entrenamientos.py")
with qa2:
    if st.button("**Ver progreso**",   use_container_width=True, key="qa_prog"):
        st.switch_page("vistas/progreso.py")
with qa3:
    if st.button("**Mis metas**",      use_container_width=True, key="qa_metas"):
        st.switch_page("vistas/metas.py")
with qa4: # cuerpo
    if st.button("**Estado muscular**", use_container_width=True, key="qa_cuerpo"):
        st.switch_page("vistas/cuerpo.py")

st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

# ── Último entreno ───────────────────────────────────────────────
ultima = c.execute(
    "SELECT nombre_rutina, inicio, duracion_min, notas FROM sesiones WHERE fin IS NOT NULL ORDER BY inicio DESC LIMIT 1"
).fetchone()

if ultima:
    try:
        ult_dt     = datetime.fromisoformat(ultima[1])
        dias_desde = (datetime.now() - ult_dt).days
        dias_txt   = "Hoy" if dias_desde == 0 else ("Ayer" if dias_desde == 1 else f"Hace {dias_desde} días")
        fecha_disp = ult_dt.strftime("%d/%m/%Y — %H:%M")
    except Exception:
        dias_txt   = "—"
        fecha_disp = str(ultima[1])

    dur_str  = f"{ultima[2]:.0f} min" if ultima[2] else "—"
    notas_html = ""
    if ultima[3]:
        notas_txt = str(ultima[3])
        notas_html = f'<p style="margin:10px 0 0; font-size:12px; color:#888; border-left:2px solid #e63946; padding-left:8px;">📝 {notas_txt}</p>'

    st.markdown(f"""
    <div style="background:#1a1a1a; border:1px solid #242424; border-radius:20px; padding:20px;">
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
            <div>
                <p style="margin:0; font-size:11px; font-weight:700; color:#555;
                          text-transform:uppercase; letter-spacing:0.1em;">Último entreno</p>
                <p style="margin:4px 0 0; font-size:19px; font-weight:700; color:#fff;">
                    {ultima[0]}
                </p>
                <p style="margin:2px 0 0; font-size:12px; color:#555;">{fecha_disp}</p>
            </div>
            <div style="text-align:right;">
                <p style="margin:0; font-size:22px; font-weight:700; color:#e63946;">{dur_str}</p>
                <p style="margin:2px 0 0; font-size:11px; color:#555;">{dias_txt}</p>
            </div>
        </div>
        {notas_html}
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

# ── Historial ────────────────────────────────────────────────────
st.markdown("""
<p style="margin:0 0 14px; font-size:13px; font-weight:700; color:#555;
          text-transform:uppercase; letter-spacing:0.1em;">
    Historial
</p>
""", unsafe_allow_html=True)

df_ses = pd.read_sql_query(
    """SELECT id, nombre_rutina, inicio, duracion_min, notas
       FROM sesiones WHERE fin IS NOT NULL
       ORDER BY inicio DESC LIMIT 20""",
    conn
)

if df_ses.empty:
    st.markdown("""
    <div style="background:#1a1a1a; border:1px dashed #2a2a2a; border-radius:20px;
                padding:40px; text-align:center;">
        <p style="font-size:32px; margin:0;">🏋️</p>
        <p style="font-size:15px; font-weight:600; color:#aaa; margin:12px 0 4px;">
            Sin entrenamientos todavía
        </p>
        <p style="font-size:13px; color:#555; margin:0;">
            Completa tu primer entreno para ver tu historial aquí
        </p>
    </div>
    """, unsafe_allow_html=True)
else:
    for _, ses in df_ses.iterrows():
        # Fecha
        try:
            fecha_dt  = datetime.fromisoformat(ses['inicio'])
            fecha_str = fecha_dt.strftime("%d/%m/%Y — %H:%M")
        except Exception:
            fecha_str = str(ses['inicio'])

        # Duración
        dur_str = f"{ses['duracion_min']:.0f} min" if ses['duracion_min'] else "—"

        # Ejercicios — construir como texto plano, nunca dentro del f-string HTML
        ejs_ses = pd.read_sql_query(
            "SELECT ejercicio, COUNT(*) as s FROM entreno WHERE sesion_id=? GROUP BY ejercicio",
            conn, params=(ses['id'],)
        )
        if not ejs_ses.empty:
            partes   = [f"{r['ejercicio']} ({r['s']}s)" for _, r in ejs_ses.iterrows()]
            ejs_txt  = " · ".join(partes)
            if len(ejs_txt) > 120:
                ejs_txt = ejs_txt[:117] + "…"
        else:
            ejs_txt = "Sin ejercicios registrados"

        # Notas — construir aparte
        notas_bloque = ""
        if ses['notas']:
            notas_segura = str(ses['notas']).replace("<", "&lt;").replace(">", "&gt;")
            notas_bloque = f'<p style="margin:10px 0 0; font-size:12px; color:#888; border-left:2px solid #444; padding-left:8px;">📝 {notas_segura}</p>'

        # Render de la tarjeta — sin lógica dentro del HTML
        st.markdown(f"""
        <div style="background:#1a1a1a; border:1px solid #242424; border-radius:20px;
                    padding:18px; margin-bottom:10px;">
            <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                <div style="flex:1; min-width:0;">
                    <p style="margin:0; font-size:16px; font-weight:700; color:#fff;">
                        {ses['nombre_rutina']}
                    </p>
                    <p style="margin:2px 0 0; font-size:12px; color:#555;">{fecha_str}</p>
                </div>
                <p style="margin:0; font-size:18px; font-weight:700; color:#e63946;
                          white-space:nowrap; padding-left:12px;">{dur_str}</p>
            </div>
            <p style="margin:10px 0 0; font-size:12px; color:#555;
                      border-top:1px solid #242424; padding-top:10px; line-height:1.6;">
                {ejs_txt}
            </p>
            {notas_bloque}
        </div>
        """, unsafe_allow_html=True)