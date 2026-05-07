import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta, date
import api_utils
import streamlit.components.v1 as components

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

# ── Calcular fatiga semanal ───────────────────────────────────────
def calcular_series_semana():
    """Retorna {musculo_en: n_series} de los últimos 7 días."""
    desde = (datetime.now() - timedelta(days=7)).isoformat()
    rows  = c.execute(
        "SELECT ejercicio, COUNT(*) as series FROM entreno WHERE fecha>=? GROUP BY ejercicio",
        (desde,)
    ).fetchall()
    resultado = {}
    for ej, series in rows:
        info = biblioteca_completa.get(ej, {})
        for m in info.get("primaryMuscles", []):
            resultado[m] = resultado.get(m, 0) + series
    return resultado

def nivel_fatiga(series):
    """Convierte número de series en nivel de fatiga."""
    if series == 0:   return "descanso"
    if series <= 4:   return "bajo"
    if series <= 10:  return "moderado"
    return "alto"

def color_fatiga(nivel):
    return {
        "descanso": "#2a2a2a",   # gris oscuro — sin trabajo
        "bajo":     "#166534",   # verde oscuro
        "moderado": "#854d0e",   # amarillo/naranja oscuro
        "alto":     "#7f1d1d",   # rojo oscuro
    }.get(nivel, "#2a2a2a")

def stroke_fatiga(nivel):
    return {
        "descanso": "#444",
        "bajo":     "#22c55e",
        "moderado": "#f59e0b",
        "alto":     "#ef4444",
    }.get(nivel, "#444")

# ── Generar SVG del cuerpo ────────────────────────────────────────
def generar_svg_cuerpo(series_map, vista="frontal"):
    """
    SVG simplificado del cuerpo humano.
    Cada músculo tiene un path/shape que se colorea según fatiga.
    """

    def m(musculo_en):
        series = series_map.get(musculo_en, 0)
        nivel  = nivel_fatiga(series)
        fill   = color_fatiga(nivel)
        stroke = stroke_fatiga(nivel)
        label  = TRAD_EN.get(musculo_en, musculo_en)
        tip    = f"{label}: {series} series ({nivel})"
        return fill, stroke, tip

    if vista == "frontal":
        # ── Vista frontal ──────────────────────────────────────
        chest_f,  chest_s,  chest_tip  = m("chest")
        bicep_f,  bicep_s,  bicep_tip  = m("biceps")
        abd_f,    abd_s,    abd_tip    = m("abdominals")
        quad_f,   quad_s,   quad_tip   = m("quadriceps")
        shoul_f,  shoul_s,  shoul_tip  = m("shoulders")
        fore_f,   fore_s,   fore_tip   = m("forearms")
        add_f,    add_s,    add_tip    = m("adductors")
        neck_f,   neck_s,   neck_tip   = m("neck")
        calv_f,   calv_s,   calv_tip   = m("calves")

        svg = f"""
<svg viewBox="0 0 220 480" xmlns="http://www.w3.org/2000/svg"
     style="max-width:100%;height:auto;display:block;margin:auto">

  <!-- Fondo -->
  <rect width="220" height="480" fill="#111" rx="12"/>

  <!-- ── CABEZA ── -->
  <ellipse cx="110" cy="38" rx="24" ry="28" fill="#333" stroke="#555" stroke-width="1.5"/>

  <!-- ── CUELLO ── -->
  <rect x="101" y="62" width="18" height="16"
        fill="{neck_f}" stroke="{neck_s}" stroke-width="1.5" rx="3">
    <title>{neck_tip}</title></rect>

  <!-- ── TORSO ── -->
  <!-- Hombros -->
  <ellipse cx="72"  cy="92" rx="20" ry="14"
           fill="{shoul_f}" stroke="{shoul_s}" stroke-width="1.5">
    <title>{shoul_tip}</title></ellipse>
  <ellipse cx="148" cy="92" rx="20" ry="14"
           fill="{shoul_f}" stroke="{shoul_s}" stroke-width="1.5">
    <title>{shoul_tip}</title></ellipse>

  <!-- Pecho izq -->
  <path d="M92,80 Q110,78 118,88 Q110,110 92,112 Q82,100 82,88 Z"
        fill="{chest_f}" stroke="{chest_s}" stroke-width="1.5">
    <title>{chest_tip}</title></path>
  <!-- Pecho der -->
  <path d="M128,80 Q110,78 102,88 Q110,110 128,112 Q138,100 138,88 Z"
        fill="{chest_f}" stroke="{chest_s}" stroke-width="1.5">
    <title>{chest_tip}</title></path>

  <!-- Abdomen (6 cuadros) -->
  <rect x="97"  y="114" width="11" height="12" rx="2"
        fill="{abd_f}" stroke="{abd_s}" stroke-width="1.2"><title>{abd_tip}</title></rect>
  <rect x="112" y="114" width="11" height="12" rx="2"
        fill="{abd_f}" stroke="{abd_s}" stroke-width="1.2"><title>{abd_tip}</title></rect>
  <rect x="97"  y="129" width="11" height="12" rx="2"
        fill="{abd_f}" stroke="{abd_s}" stroke-width="1.2"><title>{abd_tip}</title></rect>
  <rect x="112" y="129" width="11" height="12" rx="2"
        fill="{abd_f}" stroke="{abd_s}" stroke-width="1.2"><title>{abd_tip}</title></rect>
  <rect x="97"  y="144" width="11" height="12" rx="2"
        fill="{abd_f}" stroke="{abd_s}" stroke-width="1.2"><title>{abd_tip}</title></rect>
  <rect x="112" y="144" width="11" height="12" rx="2"
        fill="{abd_f}" stroke="{abd_s}" stroke-width="1.2"><title>{abd_tip}</title></rect>

  <!-- ── BRAZOS ── -->
  <!-- Bíceps izq/der -->
  <rect x="56" y="104" width="18" height="38" rx="8"
        fill="{bicep_f}" stroke="{bicep_s}" stroke-width="1.5">
    <title>{bicep_tip}</title></rect>
  <rect x="146" y="104" width="18" height="38" rx="8"
        fill="{bicep_f}" stroke="{bicep_s}" stroke-width="1.5">
    <title>{bicep_tip}</title></rect>

  <!-- Antebrazos izq/der -->
  <rect x="56" y="146" width="16" height="34" rx="7"
        fill="{fore_f}" stroke="{fore_s}" stroke-width="1.5">
    <title>{fore_tip}</title></rect>
  <rect x="148" y="146" width="16" height="34" rx="7"
        fill="{fore_f}" stroke="{fore_s}" stroke-width="1.5">
    <title>{fore_tip}</title></rect>

  <!-- ── CADERA / PELVIS ── -->
  <path d="M90,160 Q110,155 130,160 L134,186 Q110,192 86,186 Z"
        fill="#2a2a2a" stroke="#444" stroke-width="1"/>

  <!-- ── PIERNAS ── -->
  <!-- Cuádriceps izq/der -->
  <rect x="88"  y="188" width="28" height="72" rx="10"
        fill="{quad_f}" stroke="{quad_s}" stroke-width="1.5">
    <title>{quad_tip}</title></rect>
  <rect x="104" y="188" width="28" height="72" rx="10"
        fill="{quad_f}" stroke="{quad_s}" stroke-width="1.5">
    <title>{quad_tip}</title></rect>

  <!-- Aductores izq/der (franja interna) -->
  <rect x="100" y="192" width="10" height="64" rx="5"
        fill="{add_f}" stroke="{add_s}" stroke-width="1" opacity="0.8">
    <title>{add_tip}</title></rect>
  <rect x="110" y="192" width="10" height="64" rx="5"
        fill="{add_f}" stroke="{add_s}" stroke-width="1" opacity="0.8">
    <title>{add_tip}</title></rect>

  <!-- Rodillas -->
  <ellipse cx="102" cy="266" rx="13" ry="9" fill="#333" stroke="#555" stroke-width="1"/>
  <ellipse cx="118" cy="266" rx="13" ry="9" fill="#333" stroke="#555" stroke-width="1"/>

  <!-- Pantorrillas izq/der -->
  <rect x="88"  y="277" width="24" height="52" rx="10"
        fill="{calv_f}" stroke="{calv_s}" stroke-width="1.5">
    <title>{calv_tip}</title></rect>
  <rect x="108" y="277" width="24" height="52" rx="10"
        fill="{calv_f}" stroke="{calv_s}" stroke-width="1.5">
    <title>{calv_tip}</title></rect>

  <!-- Pies -->
  <ellipse cx="100" cy="333" rx="14" ry="8" fill="#333" stroke="#444" stroke-width="1"/>
  <ellipse cx="120" cy="333" rx="14" ry="8" fill="#333" stroke="#444" stroke-width="1"/>

  <!-- ── LEYENDA ── -->
  <text x="10" y="360" font-size="9" fill="#888" font-family="sans-serif">VISTA FRONTAL</text>

  <!-- Leyenda colores -->
  <rect x="10"  y="368" width="10" height="10" rx="2" fill="#2a2a2a" stroke="#444"/>
  <text x="23"  y="377" font-size="9" fill="#888" font-family="sans-serif">Sin trabajo</text>

  <rect x="10"  y="383" width="10" height="10" rx="2" fill="#166534" stroke="#22c55e"/>
  <text x="23"  y="392" font-size="9" fill="#888" font-family="sans-serif">Bajo (1-4s)</text>

  <rect x="10"  y="398" width="10" height="10" rx="2" fill="#854d0e" stroke="#f59e0b"/>
  <text x="23"  y="407" font-size="9" fill="#888" font-family="sans-serif">Moderado (5-10s)</text>

  <rect x="10"  y="413" width="10" height="10" rx="2" fill="#7f1d1d" stroke="#ef4444"/>
  <text x="23"  y="422" font-size="9" fill="#888" font-family="sans-serif">Alto (10+s)</text>
</svg>"""
        return svg

    else:
        # ── Vista dorsal ───────────────────────────────────────
        trap_f,   trap_s,   trap_tip  = m("traps")
        lat_f,    lat_s,    lat_tip   = m("lats")
        lback_f,  lback_s,  lback_tip = m("lower back")
        mback_f,  mback_s,  mback_tip = m("middle back")
        tricep_f, tricep_s, tricep_tip = m("triceps")
        glut_f,   glut_s,   glut_tip  = m("glutes")
        hamst_f,  hamst_s,  hamst_tip = m("hamstrings")
        calv_f,   calv_s,   calv_tip  = m("calves")
        shoul_f,  shoul_s,  shoul_tip = m("shoulders")
        abduct_f, abduct_s, abduct_tip = m("abductors")

        svg = f"""
<svg viewBox="0 0 220 480" xmlns="http://www.w3.org/2000/svg"
     style="max-width:100%;height:auto;display:block;margin:auto">

  <rect width="220" height="480" fill="#111" rx="12"/>

  <!-- Cabeza -->
  <ellipse cx="110" cy="38" rx="24" ry="28" fill="#333" stroke="#555" stroke-width="1.5"/>

  <!-- Trapecios -->
  <path d="M86,66 Q110,60 134,66 L138,94 Q110,86 82,94 Z"
        fill="{trap_f}" stroke="{trap_s}" stroke-width="1.5">
    <title>{trap_tip}</title></path>

  <!-- Hombros posteriores -->
  <ellipse cx="72"  cy="92" rx="20" ry="14"
           fill="{shoul_f}" stroke="{shoul_s}" stroke-width="1.5">
    <title>{shoul_tip}</title></ellipse>
  <ellipse cx="148" cy="92" rx="20" ry="14"
           fill="{shoul_f}" stroke="{shoul_s}" stroke-width="1.5">
    <title>{shoul_tip}</title></ellipse>

  <!-- Dorsales izq/der -->
  <path d="M82,94 Q74,130 80,158 Q94,164 100,160 Q96,120 96,100 Z"
        fill="{lat_f}" stroke="{lat_s}" stroke-width="1.5">
    <title>{lat_tip}</title></path>
  <path d="M138,94 Q146,130 140,158 Q126,164 120,160 Q124,120 124,100 Z"
        fill="{lat_f}" stroke="{lat_s}" stroke-width="1.5">
    <title>{lat_tip}</title></path>

  <!-- Espalda media -->
  <rect x="97" y="100" width="26" height="36" rx="4"
        fill="{mback_f}" stroke="{mback_s}" stroke-width="1.5">
    <title>{mback_tip}</title></rect>

  <!-- Espalda baja -->
  <rect x="97" y="138" width="26" height="24" rx="4"
        fill="{lback_f}" stroke="{lback_s}" stroke-width="1.5">
    <title>{lback_tip}</title></rect>

  <!-- Tríceps izq/der -->
  <rect x="56" y="104" width="18" height="38" rx="8"
        fill="{tricep_f}" stroke="{tricep_s}" stroke-width="1.5">
    <title>{tricep_tip}</title></rect>
  <rect x="146" y="104" width="18" height="38" rx="8"
        fill="{tricep_f}" stroke="{tricep_s}" stroke-width="1.5">
    <title>{tricep_tip}</title></rect>

  <!-- Glúteos izq/der -->
  <ellipse cx="101" cy="178" rx="18" ry="20"
           fill="{glut_f}" stroke="{glut_s}" stroke-width="1.5">
    <title>{glut_tip}</title></ellipse>
  <ellipse cx="119" cy="178" rx="18" ry="20"
           fill="{glut_f}" stroke="{glut_s}" stroke-width="1.5">
    <title>{glut_tip}</title></ellipse>

  <!-- Abductores (lateral cadera) -->
  <ellipse cx="84"  cy="196" rx="12" ry="18"
           fill="{abduct_f}" stroke="{abduct_s}" stroke-width="1.5">
    <title>{abduct_tip}</title></ellipse>
  <ellipse cx="136" cy="196" rx="12" ry="18"
           fill="{abduct_f}" stroke="{abduct_s}" stroke-width="1.5">
    <title>{abduct_tip}</title></ellipse>

  <!-- Isquiotibiales izq/der -->
  <rect x="88"  y="200" width="28" height="64" rx="10"
        fill="{hamst_f}" stroke="{hamst_s}" stroke-width="1.5">
    <title>{hamst_tip}</title></rect>
  <rect x="104" y="200" width="28" height="64" rx="10"
        fill="{hamst_f}" stroke="{hamst_s}" stroke-width="1.5">
    <title>{hamst_tip}</title></rect>

  <!-- Rodillas -->
  <ellipse cx="102" cy="270" rx="13" ry="9" fill="#333" stroke="#555" stroke-width="1"/>
  <ellipse cx="118" cy="270" rx="13" ry="9" fill="#333" stroke="#555" stroke-width="1"/>

  <!-- Pantorrillas izq/der -->
  <rect x="88"  y="281" width="24" height="52" rx="10"
        fill="{calv_f}" stroke="{calv_s}" stroke-width="1.5">
    <title>{calv_tip}</title></rect>
  <rect x="108" y="281" width="24" height="52" rx="10"
        fill="{calv_f}" stroke="{calv_s}" stroke-width="1.5">
    <title>{calv_tip}</title></rect>

  <!-- Pies -->
  <ellipse cx="100" cy="337" rx="14" ry="8" fill="#333" stroke="#444" stroke-width="1"/>
  <ellipse cx="120" cy="337" rx="14" ry="8" fill="#333" stroke="#444" stroke-width="1"/>

  <!-- Leyenda -->
  <text x="10" y="360" font-size="9" fill="#888" font-family="sans-serif">VISTA DORSAL</text>
  <rect x="10"  y="368" width="10" height="10" rx="2" fill="#2a2a2a" stroke="#444"/>
  <text x="23"  y="377" font-size="9" fill="#888" font-family="sans-serif">Sin trabajo</text>
  <rect x="10"  y="383" width="10" height="10" rx="2" fill="#166534" stroke="#22c55e"/>
  <text x="23"  y="392" font-size="9" fill="#888" font-family="sans-serif">Bajo (1-4s)</text>
  <rect x="10"  y="398" width="10" height="10" rx="2" fill="#854d0e" stroke="#f59e0b"/>
  <text x="23"  y="407" font-size="9" fill="#888" font-family="sans-serif">Moderado (5-10s)</text>
  <rect x="10"  y="413" width="10" height="10" rx="2" fill="#7f1d1d" stroke="#ef4444"/>
  <text x="23"  y="422" font-size="9" fill="#888" font-family="sans-serif">Alto (10+s)</text>
</svg>"""
        return svg

# ════════════════════════════════════════════════════════════════
# UI PRINCIPAL
# ════════════════════════════════════════════════════════════════
st.title("💪 Estado Muscular")

series_semana = calcular_series_semana()

# ── Selector de rango ─────────────────────────────────────────────
rango = st.radio(
    "Período",
    ["Esta semana", "Últimos 14 días", "Últimos 30 días"],
    horizontal=True,
    label_visibility="collapsed",
)
dias_map = {"Esta semana": 7, "Últimos 14 días": 14, "Últimos 30 días": 30}
dias_rango = dias_map[rango]

desde = (datetime.now() - timedelta(days=dias_rango)).isoformat()
rows  = c.execute(
    "SELECT ejercicio, COUNT(*) as series FROM entreno WHERE fecha>=? GROUP BY ejercicio",
    (desde,)
).fetchall()

series_map = {}
for ej, series in rows:
    info = biblioteca_completa.get(ej, {})
    for m in info.get("primaryMuscles", []):
        series_map[m] = series_map.get(m, 0) + series

# ── Mapas frontal y dorsal ────────────────────────────────────────
col_f, col_d = st.columns(2)

with col_f:
    st.markdown(
        "<p style='text-align:center;color:#888;font-size:13px'>Frontal</p>",
        unsafe_allow_html=True
    )

    svg_frontal = generar_svg_cuerpo(series_map, "frontal")

    components.html(
        svg_frontal,
        height=700,
        scrolling=False
    )

with col_d:
    st.markdown(
        "<p style='text-align:center;color:#888;font-size:13px'>Dorsal</p>",
        unsafe_allow_html=True
    )

    svg_dorsal = generar_svg_cuerpo(series_map, "dorsal")

    components.html(
        svg_dorsal,
        height=700,
        scrolling=False
    )

st.divider()

# ── Tabla resumen ─────────────────────────────────────────────────
st.subheader(f"📊 Series por músculo — {rango.lower()}")

if not series_map:
    st.info("Sin entrenamientos en este período.")
else:
    musculos_data = []
    for m_en, series in sorted(series_map.items(), key=lambda x: -x[1]):
        nivel = nivel_fatiga(series)
        icono = {"bajo": "🟢", "moderado": "🟡", "alto": "🔴", "descanso": "⚫"}.get(nivel, "⚫")
        musculos_data.append({
            "Músculo":   TRAD_EN.get(m_en, m_en.title()),
            "Series":    series,
            "Estado":    f"{icono} {nivel.title()}",
        })

    # Musculos sin trabajo esta semana
    todos_musculos = list(TRAD_EN.keys())
    for m in todos_musculos:
        if m not in series_map:
            musculos_data.append({
                "Músculo": TRAD_EN.get(m, m.title()),
                "Series":  0,
                "Estado":  "⚫ Sin trabajo",
            })

    df_tabla = pd.DataFrame(musculos_data).sort_values("Series", ascending=False)
    st.dataframe(df_tabla, use_container_width=True, hide_index=True)

    # ── Recomendación rápida ───────────────────────────────────
    st.divider()
    sin_trabajo = [row["Músculo"] for _, row in df_tabla.iterrows() if row["Series"] == 0]
    alta_fatiga  = [row["Músculo"] for _, row in df_tabla.iterrows() if "Alto" in row["Estado"]]

    if alta_fatiga:
        st.warning(f"⚠️ Alta carga en: **{', '.join(alta_fatiga[:3])}** — considera descanso o reducir volumen.")
    if sin_trabajo:
        st.info(f"💡 Sin trabajo esta semana: **{', '.join(sin_trabajo[:4])}**")