import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta, date
import api_utils
import streamlit.components.v1 as components
from vistas.components.bottom_nav import inject_bottom_nav

# ── CONFIGURACIÓN Y DATOS ──────────────────────────────────────────
conn = sqlite3.connect("gym_data.db", check_same_thread=False)
c    = conn.cursor()

biblioteca_completa = api_utils.cargar_biblioteca_completa()

TRAD_EN = {
    "abdominals":"Abdominales","abductors":"Abductores","adductors":"Aductores",
    "biceps":"Bíceps","calves":"Pantorrillas","chest":"Pecho",
    "forearms":"Antebrazos","glutes":"Glúteos","hamstrings":"Isquiotibiales",
    "lats":"Dorsales","lower back":"Esp. Baja","middle back":"Esp. Media",
    "neck":"Cuello","quadriceps":"Cuádriceps","shoulders":"Hombros",
    "traps":"Trapecios","triceps":"Tríceps",
}

inject_bottom_nav(active="stats")

# ── CSS GLOBAL ACTUALIZADO ────────────────────────────────────────
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
    
    /* Cambios clave para el ancho total */
    width: 100vw !important; /* Fuerza el ancho de la ventana */
    margin-left: calc(-50vw + 50%) !important; /* Centra el elemento rompiendo el padding del contenedor */
    margin-right: calc(-50vw + 50%) !important;
    
    border-radius: 0px !important; /* Opcional: quita redondeado si quieres que pegue a los bordes */
    border-top: 1px solid #262626 !important;
    border-bottom: 1px solid #262626 !important;
    border-left: none !important;
    border-right: none !important;
}

/* Ajuste de las etiquetas internas para que el contenido no pegue a los bordes del móvil */
div[role="radiogroup"] label {
    padding:4px 24px !important; /* Más padding lateral para que el texto respire */
    width: 100% !important;
    border-bottom: 1px solid #262626 !important;
}

div[role="radiogroup"] label:last-child {
    border-bottom: none !important;
}

div[role="radiogroup"] label:has(input:checked) {
    background: rgba(230, 57, 70, 0.05) !important;
}

div[role="radiogroup"] label:has(input:checked) p {
    color: #fff !important;
    font-weight: 600 !important;
}

/* Tabs y Dataframe */
.stTabs [data-baseweb="tab-list"] {
    display: flex !important;
    width: 100% !important;
    gap: 8px !important; /* Espacio entre los botones */
}

/* Forzamos a que cada pestaña individual crezca para ocupar el espacio disponible */
.stTabs [data-baseweb="tab"] {
    flex: 1 !important; /* Esto hace que los 3 tengan el mismo ancho exacto */
    justify-content: center !important;
    text-align: center !important;
    padding: 10px 0px !important;
    font-size: 14px !important;
    font-weight: 500 !important;
}

/* Ajuste adicional para que el texto no se amontone en pantallas pequeñas */
.stTabs [data-baseweb="tab"] p {
    font-size: 13px !important;
    width: 100% !important;
    text-align: center !important;
}
.stTabs [data-baseweb="tab"] { background: #171717 !important; border-radius: 12px; color: #777 !important; }
.stTabs [aria-selected="true"] { background: linear-gradient(135deg,#ef4444,#dc2626) !important; color: white !important; }

[data-testid="stDataFrame"] { background: #1a1a1a; border: 1px solid #242424; border-radius: 20px; }

div[data-testid="stButton"] > button[kind="secondary"] {
    background: transparent !important;
    border: 1px solid #242424 !important;
    color: #666 !important;
}
</style>
""", unsafe_allow_html=True)

# ── FUNCIONES LÓGICAS ─────────────────────────────────────────────
def nivel_fatiga(series):
    if series == 0:   return "descanso"
    if series <= 4:   return "bajo"
    if series <= 10:  return "moderado"
    return "alto"

def color_fatiga(nivel):
    return {"descanso": "#2a2a2a", "bajo": "#166534", "moderado": "#854d0e", "alto": "#7f1d1d"}.get(nivel, "#2a2a2a")

def stroke_fatiga(nivel):
    return {"descanso": "#444", "bajo": "#22c55e", "moderado": "#f59e0b", "alto": "#ef4444"}.get(nivel, "#444")

# ── GENERACIÓN DE SVG ─────────────────────────────────────────────
def generar_svg_cuerpo(series_map, vista="frontal"):
    def m(musculo_en):
        series = series_map.get(musculo_en, 0)
        nivel  = nivel_fatiga(series)
        fill   = color_fatiga(nivel)
        stroke = stroke_fatiga(nivel)
        label  = TRAD_EN.get(musculo_en, musculo_en)
        tip    = f"{label}: {series} series ({nivel})"
        return fill, stroke, tip

    # (Lógica de SVG frontal/dorsal igual a la anterior, ajustada a max-width 220px)
    if vista == "frontal":
        neck_f, neck_s, neck_tip = m("neck")
        shoul_f, shoul_s, shoul_tip = m("shoulders")
        chest_f, chest_s, chest_tip = m("chest")
        abd_f, abd_s, abd_tip = m("abdominals")
        bicep_f, bicep_s, bicep_tip = m("biceps")
        fore_f, fore_s, fore_tip = m("forearms")
        quad_f, quad_s, quad_tip = m("quadriceps")
        add_f, add_s, add_tip = m("adductors")
        calv_f, calv_s, calv_tip = m("calves")
        
        svg = f"""<svg viewBox="0 0 220 480" xmlns="http://www.w3.org/2000/svg" style="max-width:220px;height:auto;display:block;margin:auto;margin-bottom:20px;">
          <rect width="220" height="480" fill="#0f0f0f" rx="12"/>
          <ellipse cx="110" cy="38" rx="24" ry="28" fill="#333" stroke="#555" stroke-width="1.5"/>
          <rect x="101" y="62" width="18" height="16" fill="{neck_f}" stroke="{neck_s}" stroke-width="1.5" rx="3"></rect>
          <ellipse cx="72" cy="92" rx="20" ry="14" fill="{shoul_f}" stroke="{shoul_s}" stroke-width="1.5"></ellipse>
          <ellipse cx="148" cy="92" rx="20" ry="14" fill="{shoul_f}" stroke="{shoul_s}" stroke-width="1.5"></ellipse>
          <path d="M92,80 Q110,78 118,88 Q110,110 92,112 Q82,100 82,88 Z" fill="{chest_f}" stroke="{chest_s}" stroke-width="1.5"></path>
          <path d="M128,80 Q110,78 102,88 Q110,110 128,112 Q138,100 138,88 Z" fill="{chest_f}" stroke="{chest_s}" stroke-width="1.5"></path>
          <rect x="97" y="114" width="11" height="12" rx="2" fill="{abd_f}" stroke="{abd_s}" stroke-width="1.2"></rect>
          <rect x="112" y="114" width="11" height="12" rx="2" fill="{abd_f}" stroke="{abd_s}" stroke-width="1.2"></rect>
          <rect x="97" y="129" width="11" height="12" rx="2" fill="{abd_f}" stroke="{abd_s}" stroke-width="1.2"></rect>
          <rect x="112" y="129" width="11" height="12" rx="2" fill="{abd_f}" stroke="{abd_s}" stroke-width="1.2"></rect>
          <rect x="97" y="144" width="11" height="12" rx="2" fill="{abd_f}" stroke="{abd_s}" stroke-width="1.2"></rect>
          <rect x="112" y="144" width="11" height="12" rx="2" fill="{abd_f}" stroke="{abd_s}" stroke-width="1.2"></rect>
          <rect x="56" y="104" width="18" height="38" rx="8" fill="{bicep_f}" stroke="{bicep_s}" stroke-width="1.5"></rect>
          <rect x="146" y="104" width="18" height="38" rx="8" fill="{bicep_f}" stroke="{bicep_s}" stroke-width="1.5"></rect>
          <rect x="56" y="146" width="16" height="34" rx="7" fill="{fore_f}" stroke="{fore_s}" stroke-width="1.5"></rect>
          <rect x="148" y="146" width="16" height="34" rx="7" fill="{fore_f}" stroke="{fore_s}" stroke-width="1.5"></rect>
          <path d="M90,160 Q110,155 130,160 L134,186 Q110,192 86,186 Z" fill="#2a2a2a" stroke="#444" stroke-width="1"/>
          <rect x="88" y="188" width="28" height="72" rx="10" fill="{quad_f}" stroke="{quad_s}" stroke-width="1.5"></rect>
          <rect x="104" y="188" width="28" height="72" rx="10" fill="{quad_f}" stroke="{quad_s}" stroke-width="1.5"></rect>
          <rect x="100" y="192" width="10" height="64" rx="5" fill="{add_f}" stroke="{add_s}" stroke-width="1" opacity="0.8"></rect>
          <rect x="110" y="192" width="10" height="64" rx="5" fill="{add_f}" stroke="{add_s}" stroke-width="1" opacity="0.8"></rect>
          <ellipse cx="102" cy="266" rx="13" ry="9" fill="#333" stroke="#555" stroke-width="1"/>
          <ellipse cx="118" cy="266" rx="13" ry="9" fill="#333" stroke="#555" stroke-width="1"/>
          <rect x="88" y="277" width="24" height="52" rx="10" fill="{calv_f}" stroke="{calv_s}" stroke-width="1.5"></rect>
          <rect x="108" y="277" width="24" height="52" rx="10" fill="{calv_f}" stroke="{calv_s}" stroke-width="1.5"></rect>
        </svg>"""
        return svg
    else:
        trap_f, trap_s, trap_tip = m("traps")
        shoul_f, shoul_s, shoul_tip = m("shoulders")
        lat_f, lat_s, lat_tip = m("lats")
        mback_f, mback_s, mback_tip = m("middle back")
        lback_f, lback_s, lback_tip = m("lower back")
        tricep_f, tricep_s, tricep_tip = m("triceps")
        glut_f, glut_s, glut_tip = m("glutes")
        abduct_f, abduct_s, abduct_tip = m("abductors")
        hamst_f, hamst_s, hamst_tip = m("hamstrings")
        calv_f, calv_s, calv_tip = m("calves")

        svg = f"""<svg viewBox="0 0 220 480" xmlns="http://www.w3.org/2000/svg" style="max-width:220px;height:auto;display:block;margin:auto;margin-bottom:20px;">
          <rect width="220" height="480" fill="#0f0f0f" rx="12"/>
          <ellipse cx="110" cy="38" rx="24" ry="28" fill="#333" stroke="#555" stroke-width="1.5"/>
          <path d="M86,66 Q110,60 134,66 L138,94 Q110,86 82,94 Z" fill="{trap_f}" stroke="{trap_s}" stroke-width="1.5"></path>
          <ellipse cx="72" cy="92" rx="20" ry="14" fill="{shoul_f}" stroke="{shoul_s}" stroke-width="1.5"></ellipse>
          <ellipse cx="148" cy="92" rx="20" ry="14" fill="{shoul_f}" stroke="{shoul_s}" stroke-width="1.5"></ellipse>
          <path d="M82,94 Q74,130 80,158 Q94,164 100,160 Q96,120 96,100 Z" fill="{lat_f}" stroke="{lat_s}" stroke-width="1.5"></path>
          <path d="M138,94 Q146,130 140,158 Q126,164 120,160 Q124,120 124,100 Z" fill="{lat_f}" stroke="{lat_s}" stroke-width="1.5"></path>
          <rect x="97" y="100" width="26" height="36" rx="4" fill="{mback_f}" stroke="{mback_s}" stroke-width="1.5"></rect>
          <rect x="97" y="138" width="26" height="24" rx="4" fill="{lback_f}" stroke="{lback_s}" stroke-width="1.5"></rect>
          <rect x="56" y="104" width="18" height="38" rx="8" fill="{tricep_f}" stroke="{tricep_s}" stroke-width="1.5"></rect>
          <rect x="146" y="104" width="18" height="38" rx="8" fill="{tricep_f}" stroke="{tricep_s}" stroke-width="1.5"></rect>
          <ellipse cx="101" cy="178" rx="18" ry="20" fill="{glut_f}" stroke="{glut_s}" stroke-width="1.5"></ellipse>
          <ellipse cx="119" cy="178" rx="18" ry="20" fill="{glut_f}" stroke="{glut_s}" stroke-width="1.5"></ellipse>
          <ellipse cx="84" cy="196" rx="12" ry="18" fill="{abduct_f}" stroke="{abduct_s}" stroke-width="1.5"></ellipse>
          <ellipse cx="136" cy="196" rx="12" ry="18" fill="{abduct_f}" stroke="{abduct_s}" stroke-width="1.5"></ellipse>
          <rect x="88" y="200" width="28" height="64" rx="10" fill="{hamst_f}" stroke="{hamst_s}" stroke-width="1.5"></rect>
          <rect x="104" y="200" width="28" height="64" rx="10" fill="{hamst_f}" stroke="{hamst_s}" stroke-width="1.5"></rect>
        </svg>"""
        return svg

# ── UI PRINCIPAL ──────────────────────────────────────────────────

if st.button("← Inicio", type="secondary"):
    st.switch_page("vistas/inicio.py")

st.markdown(f"""
<div style="padding: 10px 0 20px;">
    <p style="margin:0; font-size:12px; color:#555; font-weight:600; text-transform:uppercase; letter-spacing:0.12em;">Análisis Antropométrico</p>
    <h1 style="margin:6px 0 0; font-size:28px; font-weight:700; color:#fff; letter-spacing:-0.02em; line-height:1.2;">Estado <span style="color:#e63946;">Muscular</span></h1>
</div>
""", unsafe_allow_html=True)

# ── 3. SELECTOR DE PERÍODO (FILTROS DE CÍRCULO) ──────────────────
st.markdown('<p style="margin:0 0 10px; font-size:12px; font-weight:700; color:#555; text-transform:uppercase; letter-spacing:0.1em;">Rango de Análisis</p>', unsafe_allow_html=True)

rango = st.radio(
    "Filtro",
    ["Esta semana", "Últimos 14 días", "Últimos 30 días"],
    horizontal=False, # Lo ponemos vertical para que se vea como lista de menú
    label_visibility="collapsed"
)

dias_map = {"Esta semana": 7, "Últimos 14 días": 14, "Últimos 30 días": 30}
desde = (datetime.now() - timedelta(days=dias_map[rango])).isoformat()
rows = c.execute("SELECT ejercicio, COUNT(*) as series FROM entreno WHERE fecha>=? GROUP BY ejercicio", (desde,)).fetchall()

series_map = {}
for ej, series in rows:
    info = biblioteca_completa.get(ej, {})
    for m in info.get("primaryMuscles", []):
        series_map[m] = series_map.get(m, 0) + series

# ── 4. NAVEGACIÓN POR PESTAÑAS ────────────────────────────────────
t1, t2, t3 = st.tabs(["Vista Frontal", "Vista Dorsal", "Detalles"])

with t1:
    components.html(generar_svg_cuerpo(series_map, "frontal"), height=550)

with t2:
    components.html(generar_svg_cuerpo(series_map, "dorsal"), height=550)

with t3:
    st.markdown('<p style="margin:10px 0 10px; font-size:13px; font-weight:700; color:#555; text-transform:uppercase; letter-spacing:0.1em;">Series por Grupo Muscular</p>', unsafe_allow_html=True)
    
    resumen = []
    for m_en, series in sorted(series_map.items(), key=lambda x: -x[1]):
        nivel = nivel_fatiga(series)
        icono = {"bajo": "🟢", "moderado": "🟡", "alto": "🔴", "descanso": "⚫"}.get(nivel, "⚫")
        resumen.append({"Músculo": TRAD_EN.get(m_en, m_en.title()), "Series": series, "Estado": f"{icono} {nivel.title()}"})

    for m_en in TRAD_EN.keys():
        if m_en not in series_map:
            resumen.append({"Músculo": TRAD_EN[m_en], "Series": 0, "Estado": "⚫ Descanso"})

    df_final = pd.DataFrame(resumen).sort_values("Series", ascending=False)
    st.dataframe(df_final, use_container_width=True, hide_index=True)