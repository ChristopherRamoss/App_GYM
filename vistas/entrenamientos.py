import streamlit as st
import sqlite3
import pandas as pd
import time
import api_utils
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from components.bottom_nav import inject_bottom_nav

# ─── CONEXIÓN ─────────────────────────────────────────────────────
conn = sqlite3.connect("gym_data.db", check_same_thread=False)
c    = conn.cursor()

c.execute("""CREATE TABLE IF NOT EXISTS entreno
             (id INTEGER PRIMARY KEY AUTOINCREMENT, sesion_id INTEGER,
              ejercicio TEXT, peso REAL, reps INTEGER,
              fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
c.execute("""CREATE TABLE IF NOT EXISTS rutinas
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              nombre_rutina TEXT, ejercicio TEXT, series_planificadas INTEGER)""")
c.execute("""CREATE TABLE IF NOT EXISTS ejercicios_custom
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              nombre TEXT UNIQUE, musculos TEXT DEFAULT '',
              fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
try:
    c.execute("ALTER TABLE ejercicios_custom ADD COLUMN musculos TEXT DEFAULT ''")
    conn.commit()
except Exception:
    pass
conn.commit()

# ─── NAV ──────────────────────────────────────────────────────────
inject_bottom_nav(active="rutinas")

# ─── CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');

.stApp, section[data-testid="stMain"] {
    background: #0f0f0f !important;
    font-family: 'DM Sans', sans-serif !important;
}
.block-container {
    padding-top: 0.5rem !important;
    padding-bottom: 100px !important;
    max-width: 480px !important;
}
div[data-testid="stButton"] > button[kind="primary"] {
    background: #e63946 !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    color: #fff !important;
}
div[data-testid="stButton"] > button[kind="secondary"] {
    background: #1a1a1a !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 12px !important;
    color: #aaa !important;
    font-weight: 600 !important;
}
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input {
    background: #1a1a1a !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 10px !important;
    color: #fff !important;
}
div[data-testid="stSelectbox"] > div > div {
    background: #1a1a1a !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 10px !important;
    color: #fff !important;
}
div[data-testid="stMetric"] {
    background: #1a1a1a !important;
    border: 1px solid #242424 !important;
    border-radius: 12px !important;
    padding: 10px !important;
}
div[data-testid="stMetricValue"] > div {
    font-size: 22px !important; font-weight: 700 !important; color: #fff !important;
}
div[data-testid="stMetricLabel"] > div {
    font-size: 10px !important; color: #666 !important;
    text-transform: uppercase !important; letter-spacing: 0.08em !important;
}
.stTabs [data-baseweb="tab-list"] {
    gap: 0 !important;
    border-bottom: 1px solid #2a2a2a !important;
    background: transparent !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border-radius: 0 !important;
    padding: 10px 16px !important;
    color: #555 !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    margin-bottom: -1px !important;
}
.stTabs [aria-selected="true"] {
    color: #e63946 !important;
    border-bottom: 2px solid #e63946 !important;
    background: transparent !important;
}
.stTabs [data-baseweb="tab-panel"] { padding-top: 0 !important; }
div[data-testid="stProgress"] > div {
    background: #2a2a2a !important; border-radius: 999px !important; height: 5px !important;
}
div[data-testid="stProgress"] > div > div {
    background: #e63946 !important; border-radius: 999px !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] > div {
    background: #161616 !important;
    border: 1px solid #242424 !important;
    border-radius: 16px !important;
    padding: 14px !important;
}
div[data-testid="stExpander"] {
    background: #161616 !important;
    border: 1px solid #242424 !important;
    border-radius: 14px !important;
    overflow: hidden !important;
}
div[data-testid="stExpander"] summary { color: #ccc !important; font-weight: 600 !important; }
div[data-testid="stMultiSelect"] > div {
    background: #1a1a1a !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 10px !important;
}
hr { border-color: #1e1e1e !important; margin: 16px 0 !important; }
footer { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ─── DATOS ────────────────────────────────────────────────────────
biblioteca_completa = api_utils.cargar_biblioteca_completa()
grupos_musculares   = api_utils.obtener_grupos_musculares()

TRAD = {
    "abdominals":"Abdominales","abductors":"Abductores","adductors":"Aductores",
    "biceps":"Bíceps","calves":"Pantorrillas","chest":"Pecho",
    "forearms":"Antebrazos","glutes":"Glúteos","hamstrings":"Isquiotibiales",
    "lats":"Dorsales","lower back":"Esp. Baja","middle back":"Esp. Media",
    "neck":"Cuello","quadriceps":"Cuádriceps","shoulders":"Hombros",
    "traps":"Trapecios","triceps":"Tríceps",
}
def m_es(m): return TRAD.get(m, m.title())

# ─── SESSION STATE ────────────────────────────────────────────────
_defaults = {
    "rutina_wip": [], "rutina_wip_nombre": "",
    "filtro_grupo": "Todos", "filtro_fuente": "Todos",
    "ultimo_ej_sel": None, "undo_buffer": None,
    "editando_rutina": None, "guardado_ts": 0,
    "series_para_agregar": 3, "modo_input": "Biblioteca",
    "quick_texto": "", "quick_ej_confirmado": None,
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─── HELPERS ──────────────────────────────────────────────────────
def obtener_ejercicios_custom():
    return [r[0] for r in c.execute("SELECT nombre FROM ejercicios_custom ORDER BY nombre").fetchall()]

def guardar_ejercicio_custom(nombre, musculos_en=""):
    if c.execute("SELECT id FROM ejercicios_custom WHERE nombre=?", (nombre,)).fetchone():
        return False
    try:
        c.execute("INSERT INTO ejercicios_custom (nombre, musculos) VALUES (?,?)", (nombre, musculos_en))
        conn.commit()
        return True
    except Exception:
        return False

def eliminar_ejercicio_custom(nombre):
    c.execute("DELETE FROM ejercicios_custom WHERE nombre=?", (nombre,))
    conn.commit()

def obtener_info_custom(nombre):
    row = c.execute("SELECT musculos FROM ejercicios_custom WHERE nombre=?", (nombre,)).fetchone()
    if not row: return []
    return [m.strip() for m in row[0].split(",") if m.strip()]

def obtener_ejercicios_frecuentes(n=80):
    rows = c.execute(
        "SELECT ejercicio, COUNT(*) as cnt FROM entreno GROUP BY ejercicio ORDER BY cnt DESC LIMIT ?", (n,)
    ).fetchall()
    frecuentes = [r[0] for r in rows]
    if not frecuentes:
        frecuentes = [r[0] for r in c.execute("SELECT DISTINCT ejercicio FROM rutinas ORDER BY ejercicio").fetchall()]
    for ej in obtener_ejercicios_custom():
        if ej not in frecuentes:
            frecuentes.append(ej)
    return frecuentes

def buscar_sugerencias(texto, limite=8):
    texto = texto.strip().lower()
    if not texto: return []
    frecuentes = set(obtener_ejercicios_frecuentes())
    custom     = set(obtener_ejercicios_custom())
    todos      = list(biblioteca_completa.keys()) + list(custom)
    coinciden  = [ej for ej in todos if texto in ej.lower()]
    return (sorted([e for e in coinciden if e in frecuentes]) +
            sorted([e for e in coinciden if e not in frecuentes]))[:limite]

def info_ejercicio(nombre):
    info = biblioteca_completa.get(nombre, {})
    if not info:
        info = {"url": None, "primaryMuscles": obtener_info_custom(nombre), "level": "", "equipment": ""}
    return info

def persistir_rutina_db(nombre, ejercicios_list):
    if not nombre or not ejercicios_list: return
    c.execute("DELETE FROM rutinas WHERE nombre_rutina = ?", (nombre,))
    for item in ejercicios_list:
        c.execute("INSERT INTO rutinas (nombre_rutina, ejercicio, series_planificadas) VALUES (?,?,?)",
                  (nombre, item["ejercicio"], item["series"]))
    conn.commit()

def cargar_rutina_db(nombre):
    rows = c.execute("SELECT ejercicio, series_planificadas FROM rutinas WHERE nombre_rutina=? ORDER BY rowid", (nombre,)).fetchall()
    return [{"ejercicio": ej, "series": ser,
             "url": info_ejercicio(ej).get("url") if ej in biblioteca_completa else None,
             "musculos": info_ejercicio(ej).get("primaryMuscles", []),
             "custom": ej not in biblioteca_completa}
            for ej, ser in rows]

def autoguardar():
    nombre = st.session_state.rutina_wip_nombre.strip()
    if nombre and st.session_state.rutina_wip:
        now = time.time()
        if now - st.session_state.guardado_ts > 2:
            persistir_rutina_db(nombre, st.session_state.rutina_wip)
            st.session_state.guardado_ts = now

def agregar_ejercicio_wip(ej_nombre, n_series=3):
    ej_nombre = ej_nombre.strip()
    if not ej_nombre: return False
    if ej_nombre in [e["ejercicio"] for e in st.session_state.rutina_wip]:
        st.toast(f"⚠️ {ej_nombre} ya está en la rutina")
        return False
    inf = info_ejercicio(ej_nombre)
    st.session_state.rutina_wip.append({
        "ejercicio": ej_nombre, "series": n_series,
        "url": inf.get("url") if ej_nombre in biblioteca_completa else None,
        "musculos": inf.get("primaryMuscles", []),
        "custom": ej_nombre not in biblioteca_completa,
    })
    autoguardar()
    return True

def eliminar_ejercicio_wip(idx):
    item = st.session_state.rutina_wip[idx]
    st.session_state.undo_buffer = {"ejercicio": item.copy(), "pos": idx, "ts": time.time()}
    st.session_state.rutina_wip.pop(idx)
    autoguardar()

def set_series_wip(idx, valor):
    st.session_state.rutina_wip[idx]["series"] = max(1, int(valor))
    autoguardar()

def calcular_volumen():
    wip = st.session_state.rutina_wip
    if not wip: return 0, 0, {}
    por_m = {}
    for item in wip:
        for m in item.get("musculos", []):
            me = m_es(m); por_m[me] = por_m.get(me, 0) + item["series"]
    return len(wip), sum(e["series"] for e in wip), por_m

def widget_series(key_prefix="main"):
    val = st.session_state.series_para_agregar
    c1, c2, c3 = st.columns([1, 2, 1])
    if c1.button("−", key=f"ser_menos_{key_prefix}", use_container_width=True):
        st.session_state.series_para_agregar = max(1, val - 1); st.rerun()
    c2.markdown(
        f"<div style='text-align:center;font-size:20px;font-weight:700;line-height:38px;"
        f"background:#1a1a1a;border:1px solid #2a2a2a;border-radius:10px;color:#fff'>"
        f"{st.session_state.series_para_agregar}</div>", unsafe_allow_html=True)
    if c3.button("＋", key=f"ser_mas_{key_prefix}", use_container_width=True):
        st.session_state.series_para_agregar = min(20, val + 1); st.rerun()

# ─── HERO ─────────────────────────────────────────────────────────
st.markdown("""
<div style="padding:20px 0 8px;">
    <p style="margin:0;font-size:11px;font-weight:700;color:#555;
              text-transform:uppercase;letter-spacing:0.12em;">
        Diseña · Organiza · Entrena
    </p>
    <h1 style="margin:6px 0 0;font-size:26px;font-weight:700;color:#fff;
               letter-spacing:-0.02em;">
        🏋️ Crear Rutinas
    </h1>
</div>
""", unsafe_allow_html=True)

# ─── TABS ─────────────────────────────────────────────────────────
tab_crear, tab_gestionar, tab_custom = st.tabs([
    "Crear / Editar", "Mis Rutinas", "Mis Ejercicios"
])

# ══════════════════════════════════════════════════════════════════
# TAB 1 — CREADOR
# ══════════════════════════════════════════════════════════════════
with tab_crear:
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    col_nom, col_rst = st.columns([3, 1])
    nombre_input = col_nom.text_input(
        "Nombre", value=st.session_state.rutina_wip_nombre,
        placeholder="Ej: Push Day, Piernas Lunes...",
        label_visibility="collapsed",
    )
    if nombre_input != st.session_state.rutina_wip_nombre:
        st.session_state.rutina_wip_nombre = nombre_input
        if nombre_input.strip(): autoguardar()

    if col_rst.button("🗑️ Limpiar", use_container_width=True):
        st.session_state.rutina_wip        = []
        st.session_state.rutina_wip_nombre = ""
        st.session_state.undo_buffer       = None
        st.session_state.editando_rutina   = None
        st.session_state.guardado_ts       = 0
        st.rerun()

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    mb1, mb2 = st.columns(2)
    if mb1.button("Biblioteca", use_container_width=True,
                  type="primary" if st.session_state.modo_input == "Biblioteca" else "secondary"):
        st.session_state.modo_input = "Biblioteca"; st.rerun()
    if mb2.button("Personalizados", use_container_width=True,
                  type="primary" if st.session_state.modo_input == "Personalizados" else "secondary"):
        st.session_state.modo_input = "Personalizados"; st.rerun()

    modo = st.session_state.modo_input
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    col_izq, col_der = st.columns([1, 1], gap="medium")

    # ── BIBLIOTECA ────────────────────────────────────────────────
    if modo == "Biblioteca":
        with col_izq:
            fuente = st.radio("Fuente", ["Todos", "Frecuentes"], horizontal=True,
                              index=0 if st.session_state.filtro_fuente == "Todos" else 1,
                              label_visibility="collapsed")
            st.session_state.filtro_fuente = fuente

            opciones_grupos = ["Todos"] + [m_es(g) for g in grupos_musculares]
            idx_g = opciones_grupos.index(st.session_state.filtro_grupo) \
                    if st.session_state.filtro_grupo in opciones_grupos else 0
            grupo_es = st.selectbox("Músculo", opciones_grupos, index=idx_g, key="sel_grupo")
            st.session_state.filtro_grupo = grupo_es
            grupo_en = next((en for en, es in TRAD.items() if es == grupo_es), None) \
                       if grupo_es != "Todos" else None

            if fuente == "Frecuentes":
                base = obtener_ejercicios_frecuentes()
                ejs  = sorted([e for e in base if grupo_en is None or
                               grupo_en in biblioteca_completa.get(e, {}).get("primaryMuscles", [])])
            else:
                ejs = sorted([n for n, inf in biblioteca_completa.items()
                              if grupo_en is None or grupo_en in inf.get("primaryMuscles", [])])

            if not ejs:
                st.warning("Sin ejercicios con ese filtro.")
            else:
                st.caption(f"{len(ejs)} ejercicios")
                ultimo_v = st.session_state.ultimo_ej_sel \
                           if st.session_state.ultimo_ej_sel in ejs else ejs[0]
                ej_sel = st.selectbox("Ejercicio", ejs,
                                      index=ejs.index(ultimo_v) if ultimo_v in ejs else 0,
                                      key="sel_ej_visual", label_visibility="collapsed")
                st.session_state.ultimo_ej_sel = ej_sel

                inf_sel = biblioteca_completa.get(ej_sel, {})
                if inf_sel.get("url"):
                    st.image(inf_sel["url"], use_container_width=True)
                mus_txt = ", ".join([m_es(m) for m in inf_sel.get("primaryMuscles", [])])
                nivel   = inf_sel.get("level", "").title()
                equipo  = inf_sel.get("equipment", "").title()
                # 1. BLOQUE DE CONFIGURACIÓN (Arriba)
                st.markdown('<p style="font-size:13px; font-weight:600; color:#666; text-transform:uppercase; letter-spacing:0.1em; margin-bottom:8px;">Configuración</p>', unsafe_allow_html=True)

                with st.container(border=True):
                    st.markdown("""
                    <p style="font-size:16px; font-weight:700; color:#fff; margin-bottom:12px;">
                        Series para el entrenamiento
                    </p>
                    """, unsafe_allow_html=True)

                    # Distribución 2:1
                    cs1, cs2 = st.columns([2, 1])

                    n_series = cs1.number_input(
                        "Series",
                        min_value=1,
                        max_value=20,
                        value=3,
                        step=1,
                        label_visibility="collapsed",
                        key="input_series_visual"
                    )

                    if cs2.button("➕", use_container_width=True, type="primary", key="btn_agregar_visual"):
                        if agregar_ejercicio_wip(ej_sel, n_series):
                            st.toast(f"✅ {ej_sel} — {n_series} series")
                            st.rerun()

                # Espaciador sutil
                st.markdown("<div style='height:15px'></div>", unsafe_allow_html=True)

                # 2. BLOQUE DE INFORMACIÓN TÉCNICA (Abajo)
                with st.container():
                    label_style = "font-weight:700; color:#aaa; font-size:14px; margin-bottom:2px;"
                    value_style = "color:#e63946; font-weight:600; font-size:14px;"

                    if mus_txt:
                        st.markdown(f'<p style="{label_style}">Músculo objetivo: <span style="{value_style}">{mus_txt.capitalize()}</span></p>', unsafe_allow_html=True)
                    
                    if nivel:
                        st.markdown(f'<p style="{label_style}">Nivel de dificultad: <span style="{value_style}">{nivel.capitalize()}</span></p>', unsafe_allow_html=True)
                        
                    if equipo:
                        st.markdown(f'<p style="{label_style}">Equipo requerido: <span style="{value_style}">{equipo.capitalize()}</span></p>', unsafe_allow_html=True)

    # ── PERSONALIZADOS ────────────────────────────────────────────
    else:
        with col_izq:
            texto_rapido = st.text_input(
                "quick_input", value=st.session_state.get("quick_texto", ""),
                placeholder="Escribe el nombre del ejercicio...",
                label_visibility="collapsed", key="quick_input_field",
            )
            st.session_state.quick_texto = texto_rapido

            custom_ejs   = obtener_ejercicios_custom()
            sugerencias  = buscar_sugerencias(texto_rapido) if texto_rapido.strip() else []
            texto_limpio = texto_rapido.strip()

            if sugerencias:
                st.markdown("<p style='margin:8px 0 4px;font-size:11px;font-weight:700;"
                            "color:#555;text-transform:uppercase;letter-spacing:0.08em;'>"
                            "Sugerencias</p>", unsafe_allow_html=True)
                for sug in sugerencias:
                    cs1, cs2 = st.columns([4, 1])
                    cs1.caption(sug)
                    if cs2.button("＋", key=f"sug_{sug}", use_container_width=True):
                        st.session_state.quick_ej_confirmado = sug
                        st.session_state.quick_texto = sug
                        st.rerun()

            es_nuevo     = (texto_limpio and
                            texto_limpio not in biblioteca_completa and
                            texto_limpio not in custom_ejs and not sugerencias)
            es_duplicado = bool(texto_limpio and texto_limpio in custom_ejs)
            ej_a_usar    = st.session_state.get("quick_ej_confirmado") or texto_limpio
            if not texto_limpio:
                st.session_state.quick_ej_confirmado = None
                ej_a_usar = None

            if ej_a_usar:
                inf_r      = info_ejercicio(ej_a_usar)
                musculos_r = ", ".join([m_es(m) for m in inf_r.get("primaryMuscles", [])])
                es_custom_ej = ej_a_usar not in biblioteca_completa

                if inf_r.get("url"):
                    st.image(inf_r["url"], width=100)
                else:
                    st.markdown(
                        "<div style='width:60px;height:60px;background:#1e1e1e;border-radius:10px;"
                        "display:flex;align-items:center;justify-content:center;"
                        "font-size:22px;margin-bottom:6px'>🏋️</div>", unsafe_allow_html=True)

                st.markdown(f"**{ej_a_usar}**")
                if musculos_r:   st.caption(f"💪 {musculos_r}")
                elif es_custom_ej: st.caption("🆕 Ejercicio personalizado")

                musculos_custom_sel = []
                if es_nuevo:
                    st.markdown("<p style='margin:10px 0 4px;font-size:12px;font-weight:600;"
                                "color:#aaa;'>¿Qué músculo trabaja?</p>", unsafe_allow_html=True)
                    musculos_custom_sel = st.multiselect(
                        "Músculos", options=[m_es(g) for g in grupos_musculares],
                        placeholder="Selecciona grupo muscular",
                        label_visibility="collapsed", key="quick_musculos_sel",
                    )

                if es_duplicado:
                    st.warning(f"⚠️ **{ej_a_usar}** ya existe en tus ejercicios personalizados.")

                st.caption("Series:")
                widget_series("rapido")

                btn_lbl = "➕ Crear y agregar" if es_nuevo else "➕ Agregar"
                if st.button(btn_lbl, use_container_width=True, type="primary",
                             key="btn_agregar_rapido", disabled=(es_duplicado and es_custom_ej)):
                    n = st.session_state.series_para_agregar
                    if es_nuevo:
                        TRAD_INV    = {v: k for k, v in TRAD.items()}
                        musculos_en = ",".join([TRAD_INV.get(m, m) for m in musculos_custom_sel])
                        creado = guardar_ejercicio_custom(ej_a_usar, musculos_en)
                        st.toast("🆕 Ejercicio personalizado guardado" if creado else f"⚠️ {ej_a_usar} ya existe")
                    if agregar_ejercicio_wip(ej_a_usar, n):
                        st.toast(f"✅ {ej_a_usar} — {n} series")
                    st.session_state.quick_texto         = ""
                    st.session_state.quick_ej_confirmado = None
                    st.session_state.pop("quick_musculos_sel", None)
                    st.rerun()
            else:
                st.markdown(
                    "<div style='color:#555;font-size:13px;padding:20px;"
                    "border:1px dashed #2a2a2a;border-radius:10px;text-align:center;margin-top:8px'>"
                    "Escribe para buscar en la biblioteca<br>"
                    "<small style='color:#444'>Si no aparece, se crea como ejercicio personalizado</small>"
                    "</div>", unsafe_allow_html=True)

    # ── Panel derecho ─────────────────────────────────────────────
    with col_der:
        st.markdown("<p style='margin:0 0 10px;font-size:13px;font-weight:700;"
                    "color:#555;text-transform:uppercase;letter-spacing:0.1em;'>"
                    "Tu rutina</p>", unsafe_allow_html=True)

        wip = st.session_state.rutina_wip

        if not wip:
            st.markdown(
                "<div style='color:#555;font-size:13px;padding:24px;"
                "border:1px dashed #2a2a2a;border-radius:12px;text-align:center'>"
                "Los ejercicios aparecerán aquí</div>", unsafe_allow_html=True)
        else:
            # Undo
            undo = st.session_state.undo_buffer
            if undo and (time.time() - undo["ts"]) < 8:
                cu1, cu2 = st.columns([3, 1])
                cu1.warning(f"🗑️ **{undo['ejercicio']['ejercicio']}** eliminado")
                if cu2.button("↩️", use_container_width=True):
                    st.session_state.rutina_wip.insert(min(undo["pos"], len(wip)), undo["ejercicio"])
                    st.session_state.undo_buffer = None
                    autoguardar(); st.rerun()
            elif undo:
                st.session_state.undo_buffer = None

            for i, item in enumerate(wip):
                with st.container(border=True):
                    ci, cf = st.columns([1, 4])
                    with ci:
                        if item.get("url"):
                            st.image(item["url"], use_container_width=True)
                        else:
                            st.markdown(
                                "<div style='aspect-ratio:1;background:#1e1e1e;border-radius:8px;"
                                "display:flex;align-items:center;justify-content:center;"
                                "font-size:20px'>🏋️</div>", unsafe_allow_html=True)
                    with cf:
                        badge_txt = " `custom`" if item.get("custom") else ""
                        mus_txt   = ", ".join([m_es(m) for m in item.get("musculos", [])])
                        st.markdown(f"**{item['ejercicio']}**{badge_txt}")
                        if mus_txt: st.caption(mus_txt)
                        cn, csm, csp, cdel = st.columns([2, 1, 1, 1])
                        cn.markdown(f"<div style='font-weight:700;font-size:14px;"
                                    f"color:#fff;line-height:32px'>{item['series']}s</div>",
                                    unsafe_allow_html=True)
                        if csm.button("−", key=f"sm_{i}", use_container_width=True):
                            set_series_wip(i, item["series"] - 1); st.rerun()
                        if csp.button("＋", key=f"sp_{i}", use_container_width=True):
                            set_series_wip(i, item["series"] + 1); st.rerun()
                        if cdel.button("✕", key=f"del_{i}", use_container_width=True):
                            eliminar_ejercicio_wip(i); st.rerun()

            st.divider()
            total_ej, total_ser, por_m = calcular_volumen()
            cv1, cv2 = st.columns(2)
            cv1.metric("Ejercicios", total_ej)
            cv2.metric("Series totales", total_ser)

            if por_m:
                st.markdown("<p style='margin:12px 0 6px;font-size:11px;font-weight:700;"
                            "color:#555;text-transform:uppercase;letter-spacing:0.08em;'>"
                            "Distribución muscular</p>", unsafe_allow_html=True)
                max_s = max(por_m.values())
                for mus, ser in sorted(por_m.items(), key=lambda x: -x[1]):
                    cl, cb, cn = st.columns([2, 3, 1])
                    cl.caption(mus); cb.progress(ser / max_s)
                    cn.caption(f"**{ser}**{'⚠️' if ser < 2 else ''}")

            if nombre_input.strip():
                ts   = st.session_state.guardado_ts
                hace = int(time.time() - ts) if ts > 0 else -1
                if hace >= 0:
                    st.caption("✅ Guardado" if hace < 10 else f"💾 Guardado hace {hace}s")
                else:
                    if st.button("💾 Guardar rutina", use_container_width=True, type="primary"):
                        persistir_rutina_db(nombre_input.strip(), wip)
                        st.session_state.guardado_ts = time.time()
                        st.toast(f"✅ Rutina '{nombre_input}' guardada"); st.rerun()

# ══════════════════════════════════════════════════════════════════
# TAB 2 — MIS RUTINAS
# ══════════════════════════════════════════════════════════════════
with tab_gestionar:
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    df_rutinas = pd.read_sql_query("SELECT * FROM rutinas", conn)

    if df_rutinas.empty:
        st.markdown(
            "<div style='color:#555;font-size:13px;padding:32px;"
            "border:1px dashed #2a2a2a;border-radius:12px;text-align:center'>"
            "No tienes rutinas guardadas todavía.</div>", unsafe_allow_html=True)
    else:
        rutinas_unicas = df_rutinas['nombre_rutina'].unique()
        st.caption(f"{len(rutinas_unicas)} rutina{'s' if len(rutinas_unicas)>1 else ''} guardada{'s' if len(rutinas_unicas)>1 else ''}")

        for nombre_r in rutinas_unicas:
            ejs_r = df_rutinas[df_rutinas['nombre_rutina'] == nombre_r]
            with st.expander(f"**{nombre_r}**  ·  {len(ejs_r)} ejercicios"):
                for _, fila in ejs_r.iterrows():
                    inf = info_ejercicio(fila['ejercicio'])
                    ci, cn = st.columns([1, 4])
                    if inf.get("url"):
                        ci.image(inf["url"], use_container_width=True)
                    else:
                        ci.markdown("<div style='aspect-ratio:1;background:#1e1e1e;border-radius:8px;"
                                    "display:flex;align-items:center;justify-content:center;"
                                    "font-size:18px'>🏋️</div>", unsafe_allow_html=True)
                    mus  = ", ".join([m_es(m) for m in inf.get("primaryMuscles", [])])
                    es_c = fila['ejercicio'] not in biblioteca_completa
                    cn.markdown(f"**{fila['ejercicio']}**" + (" `custom`" if es_c else ""))
                    cn.caption(f"{fila['series_planificadas']} series" + (f"  ·  {mus}" if mus else ""))

                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                col_ed, col_del_r = st.columns(2)

                if col_ed.button("✏️ Editar", key=f"edit_{nombre_r}", use_container_width=True):
                    st.session_state.rutina_wip        = cargar_rutina_db(nombre_r)
                    st.session_state.rutina_wip_nombre = nombre_r
                    st.session_state.editando_rutina   = nombre_r
                    st.session_state.guardado_ts       = time.time()
                    st.toast(f"✏️ Editando: {nombre_r}"); st.rerun()

                ck = f"confirm_del_r_{nombre_r}"
                if ck not in st.session_state: st.session_state[ck] = False

                if not st.session_state[ck]:
                    if col_del_r.button("🗑️ Eliminar", key=f"del_r_{nombre_r}", use_container_width=True):
                        st.session_state[ck] = True; st.rerun()
                else:
                    col_del_r.warning(f"¿Eliminar '{nombre_r}'?")
                    cc1, cc2 = col_del_r.columns(2)
                    if cc1.button("Sí", key=f"conf_r_{nombre_r}"):
                        c.execute("DELETE FROM rutinas WHERE nombre_rutina=?", (nombre_r,))
                        conn.commit(); del st.session_state[ck]
                        st.toast(f"🗑️ '{nombre_r}' eliminada"); st.rerun()
                    if cc2.button("No", key=f"can_r_{nombre_r}"):
                        st.session_state[ck] = False; st.rerun()

# ══════════════════════════════════════════════════════════════════
# TAB 3 — MIS EJERCICIOS PERSONALIZADOS
# ══════════════════════════════════════════════════════════════════
with tab_custom:
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    rows_custom = c.execute(
        "SELECT id, nombre, musculos, fecha_creacion FROM ejercicios_custom ORDER BY nombre"
    ).fetchall()

    if not rows_custom:
        st.markdown(
            "<div style='color:#555;font-size:13px;padding:32px;"
            "border:1px dashed #2a2a2a;border-radius:12px;text-align:center'>"
            "No tienes ejercicios personalizados todavía.<br>"
            "<small style='color:#444'>Créalos desde la pestaña Crear usando el modo Personalizados</small>"
            "</div>", unsafe_allow_html=True)
    else:
        st.caption(f"{len(rows_custom)} ejercicio{'s' if len(rows_custom)>1 else ''} personalizado{'s' if len(rows_custom)>1 else ''}")

        for eid, enombre, emusculos, efecha in rows_custom:
            mus_es = ", ".join([m_es(m.strip()) for m in emusculos.split(",") if m.strip()]) \
                     if emusculos else ""
            with st.container(border=True):
                col_ic, col_dc = st.columns([4, 1])
                with col_ic:
                    st.markdown(f"**{enombre}**")
                    st.caption(f"💪 {mus_es}" if mus_es else "Sin grupo muscular asignado")
                if col_dc.button("🗑️", key=f"del_custom_{eid}",
                                 help=f"Eliminar {enombre}", use_container_width=True):
                    eliminar_ejercicio_custom(enombre)
                    st.toast(f"🗑️ '{enombre}' eliminado"); st.rerun()