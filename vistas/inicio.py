import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta, date
import api_utils

conn = sqlite3.connect("gym_data.db", check_same_thread=False)
c    = conn.cursor()

c.execute("""CREATE TABLE IF NOT EXISTS sesiones (
    id INTEGER PRIMARY KEY AUTOINCREMENT, nombre_rutina TEXT,
    inicio TIMESTAMP, fin TIMESTAMP, duracion_min REAL, notas TEXT
)""")
conn.commit()

TRAD = {
    "abdominals":"Abdominales","biceps":"Bíceps","chest":"Pecho","lats":"Dorsales",
    "lower back":"Esp. Baja","quadriceps":"Cuádriceps","shoulders":"Hombros",
    "triceps":"Tríceps","glutes":"Glúteos","hamstrings":"Isquiotibiales",
    "calves":"Pantorrillas","traps":"Trapecios","forearms":"Antebrazos",
    "abductors":"Abductores","adductors":"Aductores","middle back":"Esp. Media",
}
biblioteca_completa = api_utils.cargar_biblioteca_completa()

# ─── Perfil ────────────────────────────────────────────────────────
perfil = c.execute("SELECT nombre FROM perfil WHERE id=1").fetchone()
nombre = perfil[0] if perfil else "Atleta"
hora   = datetime.now().hour
saludo = "Buenos días" if hora < 12 else ("Buenas tardes" if hora < 19 else "Buenas noches")

st.title(f"{saludo}, {nombre}!")

# ─── Métricas rápidas ──────────────────────────────────────────────
total_ses = c.execute("SELECT COUNT(*) FROM sesiones WHERE fin IS NOT NULL").fetchone()[0]
hoy = date.today()
lunes = hoy - timedelta(days=hoy.weekday())
ses_semana = c.execute(
    "SELECT COUNT(*) FROM sesiones WHERE fin IS NOT NULL AND DATE(inicio)>=?",
    (lunes.isoformat(),)
).fetchone()[0]
vol_semana = c.execute(
    "SELECT COALESCE(SUM(peso*reps),0) FROM entreno WHERE DATE(fecha)>=?",
    (lunes.isoformat(),)
).fetchone()[0]
ultimo_peso = c.execute("SELECT peso FROM peso_corporal ORDER BY fecha DESC LIMIT 1").fetchone()

col1, col2, col3, col4 = st.columns(4)
col1.metric("***Sesiones totales***",  total_ses)
col2.metric(" ***Esta semana***",        ses_semana)
col3.metric(" ***Volumen semana***",     f"{vol_semana:,.0f} lb")
col4.metric(" ***Peso actual***",        f"{ultimo_peso[0]:.1f} lb" if ultimo_peso else "—")

st.divider()

# ─── Última sesión + racha ─────────────────────────────────────────
ultima_ses = c.execute(
    "SELECT nombre_rutina, inicio, duracion_min, notas FROM sesiones WHERE fin IS NOT NULL ORDER BY inicio DESC LIMIT 1"
).fetchone()

if ultima_ses:
    try:
        ult_fecha = datetime.fromisoformat(ultima_ses[1])
        dias_desde = (datetime.now() - ult_fecha).days
        dias_txt   = "hoy" if dias_desde == 0 else ("ayer" if dias_desde == 1 else f"hace {dias_desde} días")
    except Exception:
        dias_txt = "—"

    col_a, col_b = st.columns([3,1])
    col_a.markdown(f"**Último entreno:** {ultima_ses[0]}")
    col_a.caption(f"📅 {dias_txt}  ·  ⏱ {ultima_ses[2]:.0f} min" if ultima_ses[2] else f"📅 {dias_txt}")
    if ultima_ses[3]:
        col_a.info(f"📝 {ultima_ses[3]}")

    # Racha de días consecutivos
    dias_ent = c.execute(
        "SELECT DISTINCT DATE(inicio) as d FROM sesiones WHERE fin IS NOT NULL ORDER BY d DESC LIMIT 30"
    ).fetchall()
    racha = 0
    if dias_ent:
        check = hoy
        for (d_str,) in dias_ent:
            try:
                d = datetime.strptime(d_str, "%Y-%m-%d").date()
                if d == check or d == check - timedelta(days=1):
                    racha += 1
                    check = d
                else:
                    break
            except Exception:
                break
    if racha > 0:
        col_b.metric("🔥 Racha", f"{racha} día{'s' if racha>1 else ''}")

st.divider()

# ─── Historial de sesiones ─────────────────────────────────────────
st.subheader("📋 Historial de Entrenamientos")

df_ses = pd.read_sql_query(
    "SELECT id, nombre_rutina, inicio, fin, duracion_min, notas FROM sesiones WHERE fin IS NOT NULL ORDER BY inicio DESC LIMIT 20",
    conn
)

if df_ses.empty:
    st.info("Aún no has completado ningún entrenamiento. ¡Ve a Entrenar y dale! 💪")
else:
    for _, ses in df_ses.iterrows():
        try:
            fecha_dt  = datetime.fromisoformat(ses['inicio'])
            fecha_str = fecha_dt.strftime("%d/%m/%Y — %H:%M")
        except Exception:
            fecha_str = str(ses['inicio'])

        dur_str = f"{ses['duracion_min']:.0f} min" if ses['duracion_min'] else "—"

        ejs_ses = pd.read_sql_query(
            """SELECT ejercicio, COUNT(*) as series, SUM(peso*reps) as vol
               FROM entreno WHERE sesion_id=? GROUP BY ejercicio""",
            conn, params=(ses['id'],)
        )

        with st.container(border=True):
            c1, c2 = st.columns([3,1])
            c1.markdown(f"**🏋️ {ses['nombre_rutina']}**")
            c1.caption(fecha_str)
            c2.metric("Duración", dur_str, label_visibility="visible")

            if not ejs_ses.empty:
                ejs_txt = "  ·  ".join(
                    f"{r['ejercicio']} ({r['series']} series)" for _, r in ejs_ses.iterrows()
                )
                st.caption(f"💪 {ejs_txt[:120]}{'…' if len(ejs_txt)>120 else ''}")
                vol_total = ejs_ses['vol'].sum()
                if vol_total:
                    st.caption(f"📦 Volumen: {vol_total:,.0f} lb")

            if ses['notas']:
                st.info(f"📝 {ses['notas']}")