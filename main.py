import streamlit as st
import sqlite3

# ─── CONFIGURACIÓN ────────────────────────────────────────────────
st.set_page_config(
    page_title="Fitness App",
    page_icon="🏋️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─── INICIALIZACIÓN DE BASE DE DATOS ──────────────────────────────
def init_db():
    conn = sqlite3.connect("gym_data.db", check_same_thread=False)
    c = conn.cursor()

    # Historial de series ejecutadas
    c.execute("""CREATE TABLE IF NOT EXISTS entreno (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        sesion_id INTEGER,
        ejercicio TEXT,
        peso      REAL,
        reps      INTEGER,
        fecha     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    # Estructura de rutinas planificadas
    c.execute("""CREATE TABLE IF NOT EXISTS rutinas (
        id                 INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre_rutina      TEXT,
        ejercicio          TEXT,
        series_planificadas INTEGER
    )""")

    # Sesiones completas de entrenamiento
    c.execute("""CREATE TABLE IF NOT EXISTS sesiones (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre_rutina TEXT,
        inicio        TIMESTAMP,
        fin           TIMESTAMP,
        duracion_min  REAL,
        notas         TEXT
    )""")

    # Perfil del usuario (un solo registro, se actualiza)
    c.execute("""CREATE TABLE IF NOT EXISTS perfil (
        id     INTEGER PRIMARY KEY,
        nombre TEXT DEFAULT 'Christopher',
        edad   INTEGER DEFAULT 25
    )""")

    # Historial de peso corporal
    c.execute("""CREATE TABLE IF NOT EXISTS peso_corporal (
        id    INTEGER PRIMARY KEY AUTOINCREMENT,
        peso  REAL,
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    # Insertar perfil por defecto si no existe
    c.execute("INSERT OR IGNORE INTO perfil (id, nombre, edad) VALUES (1, 'Christopher', 25)")

    conn.commit()
    conn.close()

init_db()

# ─── NAVEGACIÓN ───────────────────────────────────────────────────
inicio_page       = st.Page("vistas/inicio.py",          title="Inicio",       icon=":material/home:")
entreno_page      = st.Page("vistas/entrenamientos.py",  title="Crear Rutinas",icon=":material/fitness_center:")
mis_rutinas_page  = st.Page("vistas/mis_rutinas.py",     title="Entrenar",     icon=":material/play_circle:")
perfil_page       = st.Page("vistas/perfil.py",          title="Perfil",       icon=":material/person:")
estadisticas_page = st.Page("vistas/estadisticas.py",      title="Estadísticas", icon=":material/assessment:")

pg = st.navigation([inicio_page, entreno_page, mis_rutinas_page, perfil_page, estadisticas_page])
pg.run()