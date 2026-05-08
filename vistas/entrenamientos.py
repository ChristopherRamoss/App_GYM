import streamlit as st
import sqlite3
import pandas as pd
import time
import api_utils
from datetime import datetime

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
# Tabla para ejercicios personalizados (no están en el JSON)
c.execute("""CREATE TABLE IF NOT EXISTS ejercicios_custom
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              nombre TEXT UNIQUE,
              musculos TEXT DEFAULT '',
              fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
# Migración: agregar columna musculos si no existe (para DBs existentes)
try:
    c.execute("ALTER TABLE ejercicios_custom ADD COLUMN musculos TEXT DEFAULT ''")
    conn.commit()
except Exception:
    pass
conn.commit()

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

# Placeholder para ejercicios sin imagen
IMG_PLACEHOLDER = "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/exercises/Barbell_Curl/0.jpg"

# ══════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════
_defaults = {
    "rutina_wip":         [],
    "rutina_wip_nombre":  "",
    "filtro_grupo":       "Todos",
    "filtro_fuente":      "Todos",
    "ultimo_ej_sel":      None,
    "undo_buffer":        None,
    "editando_rutina":    None,
    "guardado_ts":        0,
    "series_para_agregar": 3,
    # Modo rápido
    "modo_input":          "Visual",
    "quick_texto":         "",
    "quick_ej_confirmado": None,
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ══════════════════════════════════════════════════════════════════
# HELPERS — Ejercicios personalizados
# ══════════════════════════════════════════════════════════════════
def obtener_ejercicios_custom():
    rows = c.execute("SELECT nombre FROM ejercicios_custom ORDER BY nombre").fetchall()
    return [r[0] for r in rows]

def guardar_ejercicio_custom(nombre, musculos_en=""):
    """
    Guarda ejercicio custom. musculos_en es string separado por coma (inglés).
    Retorna True si se creó nuevo, False si ya existía.
    """
    existente = c.execute(
        "SELECT id FROM ejercicios_custom WHERE nombre=?", (nombre,)
    ).fetchone()
    if existente:
        return False   # Ya existe
    try:
        c.execute(
            "INSERT INTO ejercicios_custom (nombre, musculos) VALUES (?,?)",
            (nombre, musculos_en)
        )
        conn.commit()
        return True
    except Exception:
        return False

def eliminar_ejercicio_custom(nombre):
    c.execute("DELETE FROM ejercicios_custom WHERE nombre=?", (nombre,))
    conn.commit()

def obtener_info_custom(nombre):
    """Retorna dict con musculos para ejercicios custom."""
    row = c.execute(
        "SELECT musculos FROM ejercicios_custom WHERE nombre=?", (nombre,)
    ).fetchone()
    if not row:
        return []
    return [m.strip() for m in row[0].split(",") if m.strip()]

def obtener_ejercicios_frecuentes(n=80):
    rows = c.execute(
        "SELECT ejercicio, COUNT(*) as cnt FROM entreno GROUP BY ejercicio ORDER BY cnt DESC LIMIT ?",
        (n,)
    ).fetchall()
    frecuentes = [r[0] for r in rows]
    if not frecuentes:
        frecuentes = [r[0] for r in c.execute(
            "SELECT DISTINCT ejercicio FROM rutinas ORDER BY ejercicio"
        ).fetchall()]
    # Incluir custom aunque no tengan historial
    custom = obtener_ejercicios_custom()
    for ej in custom:
        if ej not in frecuentes:
            frecuentes.append(ej)
    return frecuentes

def buscar_sugerencias(texto, limite=8):
    """
    Combina biblioteca + custom + frecuentes.
    Prioriza: frecuentes que coincidan > biblioteca que coincidan.
    """
    texto = texto.strip().lower()
    if not texto:
        return []

    frecuentes  = set(obtener_ejercicios_frecuentes())
    custom      = set(obtener_ejercicios_custom())
    todos       = list(biblioteca_completa.keys()) + list(custom)

    coinciden   = [ej for ej in todos if texto in ej.lower()]
    # Ordenar: frecuentes primero, luego alfabético
    coinciden_freq = sorted([e for e in coinciden if e in frecuentes])
    coinciden_rest = sorted([e for e in coinciden if e not in frecuentes])
    resultado = coinciden_freq + coinciden_rest

    return resultado[:limite]

def info_ejercicio(nombre):
    """Devuelve info del ejercicio (biblioteca o musculos custom si aplica)."""
    info = biblioteca_completa.get(nombre, {})
    if not info:
        musculos_custom = obtener_info_custom(nombre)
        info = {"url": None, "primaryMuscles": musculos_custom, "level": "", "equipment": ""}
    return info

# ══════════════════════════════════════════════════════════════════
# HELPERS — DB rutinas
# ══════════════════════════════════════════════════════════════════
def persistir_rutina_db(nombre, ejercicios_list):
    if not nombre or not ejercicios_list:
        return
    c.execute("DELETE FROM rutinas WHERE nombre_rutina = ?", (nombre,))
    for item in ejercicios_list:
        c.execute(
            "INSERT INTO rutinas (nombre_rutina, ejercicio, series_planificadas) VALUES (?,?,?)",
            (nombre, item["ejercicio"], item["series"])
        )
    conn.commit()

def cargar_rutina_db(nombre):
    rows = c.execute(
        "SELECT ejercicio, series_planificadas FROM rutinas WHERE nombre_rutina=? ORDER BY rowid",
        (nombre,)
    ).fetchall()
    wip = []
    for ej, ser in rows:
        inf = info_ejercicio(ej)
        wip.append({
            "ejercicio": ej,
            "series":    ser,
            "url":       inf.get("url"),
            "musculos":  inf.get("primaryMuscles", []),
            "custom":    ej not in biblioteca_completa,
        })
    return wip

def autoguardar():
    nombre = st.session_state.rutina_wip_nombre.strip()
    if nombre and st.session_state.rutina_wip:
        now = time.time()
        if now - st.session_state.guardado_ts > 2:
            persistir_rutina_db(nombre, st.session_state.rutina_wip)
            st.session_state.guardado_ts = now

# ══════════════════════════════════════════════════════════════════
# HELPERS — WIP
# ══════════════════════════════════════════════════════════════════
def agregar_ejercicio_wip(ej_nombre, n_series=3, es_custom=False):
    ej_nombre = ej_nombre.strip()
    if not ej_nombre:
        return False
    existentes = [e["ejercicio"] for e in st.session_state.rutina_wip]
    if ej_nombre in existentes:
        st.toast(f"⚠️ {ej_nombre} ya está en la rutina")
        return False
    inf = info_ejercicio(ej_nombre)
    # Si no existe en biblioteca, es custom (musculos ya guardados aparte)
    if ej_nombre not in biblioteca_completa:
        es_custom = True
    url_ej = inf.get("url") if ej_nombre in biblioteca_completa else None
    st.session_state.rutina_wip.append({
        "ejercicio": ej_nombre,
        "series":    n_series,
        "url":       url_ej,
        "musculos":  inf.get("primaryMuscles", []),
        "custom":    es_custom,
    })
    autoguardar()
    return True

def eliminar_ejercicio_wip(idx):
    item = st.session_state.rutina_wip[idx]
    st.session_state.undo_buffer = {"ejercicio": item.copy(), "pos": idx, "ts": time.time()}
    st.session_state.rutina_wip.pop(idx)
    autoguardar()

def mover_ejercicio_wip(idx, direccion):
    wip = st.session_state.rutina_wip
    nuevo_idx = idx + direccion
    if 0 <= nuevo_idx < len(wip):
        wip[idx], wip[nuevo_idx] = wip[nuevo_idx], wip[idx]
        autoguardar()

def set_series_wip(idx, valor):
    st.session_state.rutina_wip[idx]["series"] = max(1, int(valor))
    autoguardar()

def calcular_volumen_estimado():
    if not st.session_state.rutina_wip:
        return 0, 0, {}
    total_ej  = len(st.session_state.rutina_wip)
    total_ser = sum(e["series"] for e in st.session_state.rutina_wip)
    por_musculo = {}
    for item in st.session_state.rutina_wip:
        for m in item.get("musculos", []):
            me = m_es(m)
            por_musculo[me] = por_musculo.get(me, 0) + item["series"]
    return total_ej, total_ser, por_musculo

# ══════════════════════════════════════════════════════════════════
# COMPONENTE REUTILIZABLE — Selector de series compacto
# Usado tanto en modo visual como en modo rápido
# ══════════════════════════════════════════════════════════════════
def widget_series(key_prefix="main"):
    """
    Muestra − N + en una sola línea.
    Lee y escribe en st.session_state['series_para_agregar'].
    """
    val = st.session_state.series_para_agregar
    c1, c2, c3 = st.columns([1, 2, 1])
    if c1.button("−", key=f"ser_menos_{key_prefix}", use_container_width=True):
        st.session_state.series_para_agregar = max(1, val - 1)
        st.rerun()
    c2.markdown(
        f"<div style='text-align:center;font-size:20px;font-weight:700;"
        f"line-height:38px;border:1px solid #333;border-radius:8px'>"
        f"{st.session_state.series_para_agregar}</div>",
        unsafe_allow_html=True,
    )
    if c3.button("＋", key=f"ser_mas_{key_prefix}", use_container_width=True):
        st.session_state.series_para_agregar = min(20, val + 1)
        st.rerun()

# ══════════════════════════════════════════════════════════════════
# COMPONENTE REUTILIZABLE — Tarjetas de rutina en vivo
# Se usa en tab_crear (y puede reusarse en mis_rutinas si se importa)
# ══════════════════════════════════════════════════════════════════
def render_tarjetas_wip(nombre_rutina_actual):
    wip = st.session_state.rutina_wip

    if not wip:
        st.markdown(
            "<div style='color:#555;font-size:14px;padding:24px;text-align:center;"
            "border:1px dashed #333;border-radius:10px;margin-top:4px'>"
            "Los ejercicios que agregues aparecerán aquí</div>",
            unsafe_allow_html=True,
        )
        return

    # ── Undo ──────────────────────────────────────────────────
    undo = st.session_state.undo_buffer
    if undo and (time.time() - undo["ts"]) < 8:
        cu1, cu2 = st.columns([3, 1])
        cu1.warning(f"🗑️ **{undo['ejercicio']['ejercicio']}** eliminado")
        if cu2.button("↩️ Deshacer", use_container_width=True):
            pos = min(undo["pos"], len(wip))
            st.session_state.rutina_wip.insert(pos, undo["ejercicio"])
            st.session_state.undo_buffer = None
            autoguardar()
            st.rerun()
    elif undo:
        st.session_state.undo_buffer = None

    # ── Tarjetas ──────────────────────────────────────────────
    for i, item in enumerate(wip):
        with st.container(border=True):
            col_img, col_info = st.columns([1, 4])

            # Thumbnail pequeño (solo si hay imagen real)
            with col_img:
                url = item.get("url")
                if url:
                    st.image(url, use_container_width=True)
                else:
                    st.markdown(
                        "<div style='width:100%;aspect-ratio:1;background:#1e1e1e;"
                        "border-radius:8px;display:flex;align-items:center;"
                        "justify-content:center;font-size:24px'>🏋️</div>",
                        unsafe_allow_html=True
                    )

            with col_info:
                # Nombre + badge custom
                badge = " `custom`" if item.get("custom") else ""
                musculos_txt = ", ".join([m_es(m) for m in item.get("musculos", [])])
                st.markdown(f"**{item['ejercicio']}**{badge}")
                if musculos_txt:
                    st.caption(musculos_txt)

                # UNA SOLA FILA: #series | − | + | ✕
                c_num, c_sm, c_sp, c_del = st.columns([2, 1, 1, 1])
                c_num.markdown(
                    f"<div style='font-weight:700;font-size:15px;line-height:36px'>"
                    f"{item['series']} series</div>",
                    unsafe_allow_html=True,
                )
                if c_sm.button("−", key=f"sm_{i}", use_container_width=True):
                    set_series_wip(i, item["series"] - 1)
                    st.rerun()
                if c_sp.button("＋", key=f"sp_{i}", use_container_width=True):
                    set_series_wip(i, item["series"] + 1)
                    st.rerun()
                if c_del.button("✕", key=f"del_{i}", use_container_width=True):
                    eliminar_ejercicio_wip(i)
                    st.rerun()

    # ── Volumen estimado ───────────────────────────────────────
    st.divider()
    total_ej, total_ser, por_musculo = calcular_volumen_estimado()
    cv1, cv2 = st.columns(2)
    cv1.metric("Ejercicios", total_ej)
    cv2.metric("Series totales", total_ser)

    if por_musculo:
        st.caption("**Distribución por músculo:**")
        max_s = max(por_musculo.values())
        for mus, ser in sorted(por_musculo.items(), key=lambda x: -x[1]):
            cl, cb, cn = st.columns([2, 3, 1])
            cl.caption(mus)
            cb.progress(ser / max_s)
            warn = " ⚠️" if ser < 2 else ""
            cn.caption(f"**{ser}**{warn}")

    # ── Estado de guardado ─────────────────────────────────────
    if nombre_rutina_actual.strip() and wip:
        ts = st.session_state.guardado_ts
        if ts > 0:
            hace = int(time.time() - ts)
            st.caption("✅ Guardado" if hace < 10 else f"💾 Guardado hace {hace}s")
        else:
            if st.button("💾 Guardar rutina", use_container_width=True, type="primary"):
                persistir_rutina_db(nombre_rutina_actual.strip(), wip)
                st.session_state.guardado_ts = time.time()
                st.toast(f"✅ Rutina '{nombre_rutina_actual}' guardada")
                st.rerun()

# ══════════════════════════════════════════════════════════════════
# UI PRINCIPAL
# ══════════════════════════════════════════════════════════════════
st.title("🏋️ Crear Rutinas")

tab_crear, tab_gestionar, tab_custom = st.tabs(["✏️ Crear / Editar", "📋 Mis Rutinas", "🛠️ Mis Ejercicios"])

# ══════════════════════════════════════════════════════════════════
# TAB 1 — CREADOR EN VIVO
# ══════════════════════════════════════════════════════════════════
with tab_crear:

    # ── Nombre ────────────────────────────────────────────────
    col_nom, col_rst = st.columns([3, 1])
    nombre_input = col_nom.text_input(
        "Nombre",
        value=st.session_state.rutina_wip_nombre,
        placeholder="Ej: Push Day, Piernas...",
        label_visibility="collapsed",
    )
    if nombre_input != st.session_state.rutina_wip_nombre:
        st.session_state.rutina_wip_nombre = nombre_input
        if nombre_input.strip():
            autoguardar()

    if col_rst.button("🗑️ Limpiar", use_container_width=True):
        st.session_state.rutina_wip        = []
        st.session_state.rutina_wip_nombre = ""
        st.session_state.undo_buffer       = None
        st.session_state.editando_rutina   = None
        st.session_state.guardado_ts       = 0
        st.rerun()

    st.divider()

    # ── Toggle modo Visual / Rápido ───────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        # Botón de Biblioteca
        # Usamos type="primary" para resaltar el seleccionado basándonos en el session_state
        if st.button("Biblioteca", use_container_width=True, 
                    type="primary" if st.session_state.modo_input == "Biblioteca" else "secondary"):
            st.session_state.modo_input = "Biblioteca"
            st.rerun()

    with col2:
        # Botón de Personalizados
        if st.button("Personalizados", use_container_width=True, 
                    type="primary" if st.session_state.modo_input == "Personalizados" else "secondary"):
            st.session_state.modo_input = "Personalizados"
            st.rerun()

    # Asignamos la variable modo para que el resto de tu código funcione igual
    modo = st.session_state.modo_input

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    col_izq, col_der = st.columns([1, 1], gap="medium")

    # ══════════════════════════════════════════════════════════
    # MODO VISUAL — igual que antes, series compactas
    # ══════════════════════════════════════════════════════════
    if modo == "Biblioteca":
        with col_izq:
            # Fuente
            fuente = st.radio(
                "Fuente",
                ["Todos", "Frecuentes"],
                horizontal=True,
                index=0 if st.session_state.filtro_fuente == "Todos" else 1,
                label_visibility="collapsed",
            )
            st.session_state.filtro_fuente = fuente

            # Filtro músculo
            opciones_grupos = ["Todos"] + [m_es(g) for g in grupos_musculares]
            idx_g = (opciones_grupos.index(st.session_state.filtro_grupo)
                     if st.session_state.filtro_grupo in opciones_grupos else 0)
            grupo_es = st.selectbox("🎯 Músculo", opciones_grupos,
                                    index=idx_g, key="sel_grupo")
            st.session_state.filtro_grupo = grupo_es

            grupo_en = next(
                (en for en, es in TRAD.items() if es == grupo_es), None
            ) if grupo_es != "Todos" else None

            # Lista según fuente + filtro
            if fuente == "Frecuentes":
                base = obtener_ejercicios_frecuentes()
                ejs  = sorted([e for e in base
                               if grupo_en is None or
                               grupo_en in biblioteca_completa.get(e, {}).get("primaryMuscles", [])])
            else:
                ejs = sorted([
                    n for n, inf in biblioteca_completa.items()
                    if grupo_en is None or grupo_en in inf.get("primaryMuscles", [])
                ])

            if not ejs:
                st.warning("Sin ejercicios con ese filtro.")
            else:
                st.caption(f"{len(ejs)} ejercicios")
                ultimo_v = (st.session_state.ultimo_ej_sel
                            if st.session_state.ultimo_ej_sel in ejs else ejs[0])
                idx_ej = ejs.index(ultimo_v) if ultimo_v in ejs else 0

                ej_sel = st.selectbox("Ejercicio", ejs, index=idx_ej,
                                      key="sel_ej_visual",
                                      label_visibility="collapsed")
                st.session_state.ultimo_ej_sel = ej_sel

                # Preview
                inf_sel = biblioteca_completa.get(ej_sel, {})
                if inf_sel.get("url"):
                    st.image(inf_sel["url"], use_container_width=True)
                musculos_txt = ", ".join([m_es(m) for m in inf_sel.get("primaryMuscles", [])])
                nivel_txt    = inf_sel.get("level", "").title()
                equipo_txt   = inf_sel.get("equipment", "").title()
                if musculos_txt: st.caption(f"💪 {musculos_txt}")
                if nivel_txt:    st.caption(f"📊 {nivel_txt}  ·  🔧 {equipo_txt}")

                # Series compacto
                st.caption("Series:")
                widget_series("visual")

                # Agregar
                if st.button("➕ Agregar", use_container_width=True,
                             type="primary", key="btn_agregar_visual"):
                    n = st.session_state.series_para_agregar
                    if agregar_ejercicio_wip(ej_sel, n):
                        st.toast(f"✅ {ej_sel} — {n} series")
                    st.rerun()

    # ══════════════════════════════════════════════════════════
    # MODO RÁPIDO — text_input libre + sugerencias + crear custom
    # ══════════════════════════════════════════════════════════
    else:
        with col_izq:
            # ── Text input libre ──────────────────────────────
            texto_rapido = st.text_input(
                "quick_input",
                value=st.session_state.get("quick_texto", ""),
                placeholder="Escribe el nombre del ejercicio...",
                label_visibility="collapsed",
                key="quick_input_field",
            )
            st.session_state.quick_texto = texto_rapido

            custom_ejs    = obtener_ejercicios_custom()
            sugerencias   = buscar_sugerencias(texto_rapido) if texto_rapido.strip() else []
            texto_limpio  = texto_rapido.strip()

            # ── Sugerencias ───────────────────────────────────
            if sugerencias:
                st.caption("Sugerencias:")
                for sug in sugerencias:
                    col_sug, col_add_sug = st.columns([4, 1])
                    col_sug.caption(sug)
                    if col_add_sug.button("＋", key=f"sug_{sug}", use_container_width=True):
                        st.session_state.quick_ej_confirmado = sug
                        st.session_state.quick_texto = sug
                        st.rerun()

            # Determinar si es ejercicio nuevo (no existe en ningún lado)
            es_nuevo = (
                texto_limpio and
                texto_limpio not in biblioteca_completa and
                texto_limpio not in custom_ejs and
                not sugerencias
            )

            # Detectar duplicado en custom
            es_duplicado = texto_limpio and texto_limpio in custom_ejs

            ej_a_usar = st.session_state.get("quick_ej_confirmado") or texto_limpio
            if not texto_limpio:
                st.session_state.quick_ej_confirmado = None
                ej_a_usar = None

            if ej_a_usar:
                inf_r      = info_ejercicio(ej_a_usar)
                musculos_r = ", ".join([m_es(m) for m in inf_r.get("primaryMuscles", [])])
                es_custom_ej = ej_a_usar not in biblioteca_completa

                # Preview
                if inf_r.get("url"):
                    st.image(inf_r["url"], width=100)
                st.markdown(f"**{ej_a_usar}**")
                if musculos_r:
                    st.caption(f"💪 {musculos_r}")
                elif es_custom_ej:
                    st.caption("🆕 Ejercicio personalizado")

                # ── Selector de músculos para ejercicios nuevos ──
                musculos_custom_sel = []
                if es_nuevo:
                    st.caption("¿Qué músculo trabaja?")
                    opciones_m = [m_es(g) for g in grupos_musculares]
                    musculos_custom_sel = st.multiselect(
                        "Músculos",
                        options=opciones_m,
                        placeholder="Selecciona uno o más grupos musculares",
                        label_visibility="collapsed",
                        key="quick_musculos_sel",
                    )

                # Aviso de duplicado
                if es_duplicado:
                    st.warning(f"⚠️ **{ej_a_usar}** ya existe en tus ejercicios personalizados.")

                # Series
                st.caption("Series:")
                widget_series("rapido")

                btn_lbl = "➕ Crear y agregar" if es_nuevo else "➕ Agregar"
                btn_disabled = es_duplicado and es_custom_ej

                if st.button(btn_lbl, use_container_width=True,
                             type="primary", key="btn_agregar_rapido",
                             disabled=btn_disabled):
                    n = st.session_state.series_para_agregar

                    # Guardar custom con músculos ANTES de agregar al WIP
                    if es_nuevo:
                        # Convertir nombres ES → EN para guardar
                        TRAD_INV = {v: k for k, v in TRAD.items()}
                        musculos_en = ",".join([TRAD_INV.get(m, m) for m in musculos_custom_sel])
                        creado = guardar_ejercicio_custom(ej_a_usar, musculos_en)
                        if not creado:
                            st.toast(f"⚠️ {ej_a_usar} ya existe")
                        else:
                            st.toast("🆕 Ejercicio personalizado guardado")

                    if agregar_ejercicio_wip(ej_a_usar, n):
                        st.toast(f"✅ {ej_a_usar} — {n} series")

                    st.session_state.quick_texto         = ""
                    st.session_state.quick_ej_confirmado = None
                    st.session_state.pop("quick_musculos_sel", None)
                    st.rerun()

            else:
                st.markdown(
                    "<div style='color:#555;font-size:13px;padding:16px;"
                    "border:1px dashed #333;border-radius:8px;text-align:center'>"
                    "Escribe arriba para buscar<br>"
                    "<small>Si no aparece, se crea como ejercicio personalizado</small></div>",
                    unsafe_allow_html=True,
                )

    # ── Panel derecho: rutina en vivo (compartido por ambos modos) ──
    with col_der:
        st.subheader("📋 Tu rutina")
        render_tarjetas_wip(nombre_input)

# ══════════════════════════════════════════════════════════════════
# TAB 2 — GESTIONAR RUTINAS EXISTENTES
# ══════════════════════════════════════════════════════════════════
with tab_gestionar:
    df_rutinas = pd.read_sql_query("SELECT * FROM rutinas", conn)

    if df_rutinas.empty:
        st.info("No tienes rutinas guardadas. ¡Crea una en la pestaña anterior!")
    else:
        rutinas_unicas = df_rutinas['nombre_rutina'].unique()
        st.caption(f"{len(rutinas_unicas)} rutinas guardadas")

        for nombre_r in rutinas_unicas:
            ejs_rutina = df_rutinas[df_rutinas['nombre_rutina'] == nombre_r]

            with st.expander(f"📋 {nombre_r}  ({len(ejs_rutina)} ejercicios)"):
                for _, fila in ejs_rutina.iterrows():
                    inf = info_ejercicio(fila['ejercicio'])
                    ci, cn = st.columns([1, 4])
                    url_t = inf.get("url") or IMG_PLACEHOLDER
                    ci.image(url_t, use_container_width=True)
                    musculos = ", ".join([m_es(m) for m in inf.get("primaryMuscles", [])])
                    cn.markdown(f"**{fila['ejercicio']}**"
                                + (" `custom`" if fila['ejercicio'] not in biblioteca_completa else ""))
                    cn.caption(f"{fila['series_planificadas']} series"
                               + (f"  ·  {musculos}" if musculos else ""))

                st.divider()
                col_ed, col_del_r = st.columns(2)

                if col_ed.button("✏️ Editar", key=f"edit_{nombre_r}",
                                 use_container_width=True):
                    st.session_state.rutina_wip        = cargar_rutina_db(nombre_r)
                    st.session_state.rutina_wip_nombre = nombre_r
                    st.session_state.editando_rutina   = nombre_r
                    st.session_state.guardado_ts       = time.time()
                    st.toast(f"✏️ Editando: {nombre_r}")
                    st.rerun()

                confirm_key = f"confirm_del_r_{nombre_r}"
                if confirm_key not in st.session_state:
                    st.session_state[confirm_key] = False

                if not st.session_state[confirm_key]:
                    if col_del_r.button("🗑️ Eliminar", key=f"del_r_{nombre_r}",
                                        use_container_width=True):
                        st.session_state[confirm_key] = True
                        st.rerun()
                else:
                    col_del_r.warning(f"¿Eliminar '{nombre_r}'?")
                    cc1, cc2 = col_del_r.columns(2)
                    if cc1.button("Sí", key=f"conf_r_{nombre_r}"):
                        c.execute("DELETE FROM rutinas WHERE nombre_rutina=?", (nombre_r,))
                        conn.commit()
                        del st.session_state[confirm_key]
                        st.toast(f"🗑️ '{nombre_r}' eliminada")
                        st.rerun()
                    if cc2.button("No", key=f"can_r_{nombre_r}"):
                        st.session_state[confirm_key] = False
                        st.rerun()

# ══════════════════════════════════════════════════════════════════
# TAB 3 — EJERCICIOS PERSONALIZADOS
# ══════════════════════════════════════════════════════════════════
with tab_custom:
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    rows_custom = c.execute(
        "SELECT id, nombre, musculos, fecha_creacion FROM ejercicios_custom ORDER BY nombre"
    ).fetchall()

    if not rows_custom:
        st.markdown(
            "<div style='color:#555;font-size:13px;padding:24px;"
            "border:1px dashed #333;border-radius:10px;text-align:center'>"
            "No tienes ejercicios personalizados todavía.<br>"
            "<small>Créalos desde Personalizados</small></div>",
            unsafe_allow_html=True,
        )
    else:
        st.caption(f"{len(rows_custom)} ejercicio{'s' if len(rows_custom)>1 else ''} personalizado{'s' if len(rows_custom)>1 else ''}")

        for eid, enombre, emusculos, efecha in rows_custom:
            musculos_es = ""
            if emusculos:
                musculos_es = ", ".join([m_es(m.strip()) for m in emusculos.split(",") if m.strip()])

            with st.container(border=True):
                col_info_c, col_del_c = st.columns([4, 1])
                with col_info_c:
                    st.markdown(f"**{enombre}**")
                    if musculos_es:
                        st.caption(f"💪 {musculos_es}")
                    else:
                        st.caption("Sin grupo muscular asignado")
                if col_del_c.button("🗑️", key=f"del_custom_{eid}",
                                    help=f"Eliminar {enombre}",
                                    use_container_width=True):
                    eliminar_ejercicio_custom(enombre)
                    st.toast(f"🗑️ '{enombre}' eliminado")
                    st.rerun()