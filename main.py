import streamlit as st
import sqlite3

st.set_page_config(
    page_title="Fitness App",
    page_icon="🏋️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

def init_db():
    conn = sqlite3.connect("gym_data.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS entreno (
        id INTEGER PRIMARY KEY AUTOINCREMENT, sesion_id INTEGER,
        ejercicio TEXT, peso REAL, reps INTEGER,
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS rutinas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre_rutina TEXT, ejercicio TEXT, series_planificadas INTEGER)""")
    c.execute("""CREATE TABLE IF NOT EXISTS sesiones (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nombre_rutina TEXT,
        inicio TIMESTAMP, fin TIMESTAMP, duracion_min REAL, notas TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS perfil (
        id INTEGER PRIMARY KEY,
        nombre TEXT DEFAULT 'Christopher', edad INTEGER DEFAULT 25)""")
    c.execute("""CREATE TABLE IF NOT EXISTS peso_corporal (
        id INTEGER PRIMARY KEY AUTOINCREMENT, peso REAL,
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("INSERT OR IGNORE INTO perfil (id,nombre,edad) VALUES (1,'Christopher',25)")
    conn.commit()
    conn.close()

init_db()

# Navegación — el CSS lo inyecta cada vista individualmente
inicio_page       = st.Page("vistas/inicio.py",          title="Inicio",          icon="🏠")
entreno_page      = st.Page("vistas/entrenamientos.py",  title="Rutinas",         icon="📋")
mis_rutinas_page  = st.Page("vistas/mis_rutinas.py",     title="Entrenar",        icon="▶️")
estadisticas_page = st.Page("vistas/estadisticas.py",    title="Estadísticas",    icon="📊")
progreso_page     = st.Page("vistas/progreso.py",        title="Progreso",        icon="📈")
metas_page        = st.Page("vistas/metas.py",           title="Metas",           icon="🎯")
cuerpo_page       = st.Page("vistas/cuerpo.py",          title="Estado Muscular", icon="💪")
perfil_page       = st.Page("vistas/perfil.py",          title="Perfil",          icon="👤")

pg = st.navigation([
    inicio_page, mis_rutinas_page, entreno_page,
    estadisticas_page, progreso_page, metas_page,
    cuerpo_page, perfil_page,
])
pg.run()