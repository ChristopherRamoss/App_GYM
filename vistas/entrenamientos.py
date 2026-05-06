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

# ══════════════════════════════════════════════════════════════════
# SESSION STATE — todo el estado vive aquí
# ══════════════════════════════════════════════════════════════════
# rutina_wip: lista de dicts ordenada que representa la rutina en construcción
# [{"ejercicio": str, "series": int, "url": str, "musculos": [str]}]
_defaults = {
    "rutina_wip":        [],       # Rutina en construcción
    "rutina_wip_nombre": "",       # Nombre de la rutina activa
    "filtro_grupo":      "Todos",  # Filtro de músculo persistente
    "filtro_fuente":     "Biblioteca completa",  # Biblioteca / Frecuentes
    "ultimo_ej_sel":     None,     # Último ejercicio seleccionado (para continuidad)
    "undo_buffer":       None,     # {"ejercicio": dict, "pos": int, "ts": float}
    "editando_rutina":   None,     # nombre de rutina en edición (None = modo creación)
    "guardado_ts":       0,        # timestamp del último guardado en DB
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ══════════════════════════════════════════════════════════════════
# HELPERS DB
# ══════════════════════════════════════════════════════════════════
def persistir_rutina_db(nombre, ejercicios_list):
    """Guarda (o reemplaza) la rutina completa en DB."""
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
    """Carga una rutina de la DB a session_state."""
    rows = c.execute(
        "SELECT ejercicio, series_planificadas FROM rutinas WHERE nombre_rutina=? ORDER BY rowid",
        (nombre,)
    ).fetchall()
    wip = []
    for ej, ser in rows:
        info = biblioteca_completa.get(ej, {})
        wip.append({
            "ejercicio": ej,
            "series":    ser,
            "url":       info.get("url"),
            "musculos":  info.get("primaryMuscles", []),
        })
    return wip

def obtener_ejercicios_frecuentes(n=60):
    """Top N ejercicios más usados en historial."""
    rows = c.execute(
        "SELECT ejercicio, COUNT(*) as cnt FROM entreno GROUP BY ejercicio ORDER BY cnt DESC LIMIT ?",
        (n,)
    ).fetchall()
    frecuentes = [r[0] for r in rows]
    # Si no hay historial, caer a ejercicios en rutinas
    if not frecuentes:
        frecuentes = [r[0] for r in c.execute(
            "SELECT DISTINCT ejercicio FROM rutinas ORDER BY ejercicio"
        ).fetchall()]
    return frecuentes

def autoguardar():
    """Persiste en DB si han pasado >2s desde último guardado y hay datos."""
    nombre = st.session_state.rutina_wip_nombre.strip()
    if nombre and st.session_state.rutina_wip:
        now = time.time()
        if now - st.session_state.guardado_ts > 2:
            persistir_rutina_db(nombre, st.session_state.rutina_wip)
            st.session_state.guardado_ts = now

# ══════════════════════════════════════════════════════════════════
# HELPERS WIP (Workout In Progress)
# ══════════════════════════════════════════════════════════════════
def agregar_ejercicio_wip(ej_nombre):
    """Agrega un ejercicio a la rutina en construcción."""
    info = biblioteca_completa.get(ej_nombre, {})
    # Evitar duplicados
    existentes = [e["ejercicio"] for e in st.session_state.rutina_wip]
    if ej_nombre in existentes:
        st.toast(f"⚠️ {ej_nombre} ya está en la rutina")
        return False
    st.session_state.rutina_wip.append({
        "ejercicio": ej_nombre,
        "series":    3,
        "url":       info.get("url"),
        "musculos":  info.get("primaryMuscles", []),
    })
    autoguardar()
    return True

def eliminar_ejercicio_wip(idx):
    """Elimina con buffer de undo."""
    item = st.session_state.rutina_wip[idx]
    st.session_state.undo_buffer = {"ejercicio": item.copy(), "pos": idx, "ts": time.time()}
    st.session_state.rutina_wip.pop(idx)
    autoguardar()

def mover_ejercicio_wip(idx, direccion):
    """Mueve ejercicio arriba (-1) o abajo (+1)."""
    wip = st.session_state.rutina_wip
    nuevo_idx = idx + direccion
    if 0 <= nuevo_idx < len(wip):
        wip[idx], wip[nuevo_idx] = wip[nuevo_idx], wip[idx]
        autoguardar()

def set_series_wip(idx, valor):
    """Actualiza el número de series de un ejercicio."""
    st.session_state.rutina_wip[idx]["series"] = max(1, int(valor))
    autoguardar()

def calcular_volumen_estimado():
    """Calcula total de ejercicios, series y desglose por músculo."""
    if not st.session_state.rutina_wip:
        return 0, 0, {}
    total_ej  = len(st.session_state.rutina_wip)
    total_ser = sum(e["series"] for e in st.session_state.rutina_wip)
    por_musculo = {}
    for item in st.session_state.rutina_wip:
        for m in item["musculos"]:
            me = m_es(m)
            por_musculo[me] = por_musculo.get(me, 0) + item["series"]
    return total_ej, total_ser, por_musculo

# ══════════════════════════════════════════════════════════════════
# UI PRINCIPAL
# ══════════════════════════════════════════════════════════════════
st.title("🏋️ Crear Rutinas")

# ── Tabs: Crear nueva / Gestionar existentes ──────────────────────
tab_crear, tab_gestionar = st.tabs(["✏️ Crear / Editar", "📋 Mis Rutinas"])

# ══════════════════════════════════════════════════════════════════
# TAB 1 — CREADOR EN VIVO
# ══════════════════════════════════════════════════════════════════
with tab_crear:

    # ── Nombre de la rutina (requisito primero) ───────────────
    col_nom, col_rst = st.columns([3, 1])
    nombre_input = col_nom.text_input(
        "Nombre de la rutina",
        value=st.session_state.rutina_wip_nombre,
        placeholder="Ej: Push Day, Piernas Lunes...",
        label_visibility="collapsed",
    )

    # Detectar cambio de nombre
    if nombre_input != st.session_state.rutina_wip_nombre:
        st.session_state.rutina_wip_nombre = nombre_input
        if nombre_input.strip():
            autoguardar()

    if col_rst.button("🗑️ Limpiar", use_container_width=True, help="Limpiar y empezar de nuevo"):
        st.session_state.rutina_wip        = []
        st.session_state.rutina_wip_nombre = ""
        st.session_state.undo_buffer       = None
        st.session_state.editando_rutina   = None
        st.rerun()

    if not nombre_input.strip():
        st.info("👆 Escribe un nombre para la rutina para empezar a construirla.")

    st.divider()

    # ══════════════════════════════════════════════════════════
    # PANEL IZQUIERDO: Selector + Panel derecho: Rutina en vivo
    # En móvil se apilan (Streamlit lo hace automático con columns)
    # ══════════════════════════════════════════════════════════
    col_sel, col_rutina = st.columns([1, 1], gap="medium")

    # ─────────────────────────────────────────────────────────
    # COLUMNA IZQUIERDA — Selector de ejercicios
    # ─────────────────────────────────────────────────────────
    with col_sel:
        st.subheader("➕ Agregar ejercicio")

        # Fuente: Biblioteca / Frecuentes
        fuente = st.radio(
            "Fuente",
            ["Biblioteca completa", "⭐ Frecuentes"],
            index=0 if st.session_state.filtro_fuente == "Biblioteca completa" else 1,
            horizontal=True,
            label_visibility="collapsed",
        )
        st.session_state.filtro_fuente = fuente

        # Filtro de grupo muscular (persistente)
        opciones_grupos = ["Todos"] + [m_es(g) for g in grupos_musculares]
        idx_grupo_actual = (
            opciones_grupos.index(st.session_state.filtro_grupo)
            if st.session_state.filtro_grupo in opciones_grupos else 0
        )
        grupo_sel_es = st.selectbox(
            "🎯 Músculo",
            opciones_grupos,
            index=idx_grupo_actual,
            key="sel_grupo_muscular",
        )
        st.session_state.filtro_grupo = grupo_sel_es

        # Convertir ES → EN
        grupo_sel_en = None
        if grupo_sel_es != "Todos":
            for en, es in TRAD.items():
                if es == grupo_sel_es:
                    grupo_sel_en = en
                    break

        # Obtener lista según fuente + filtro
        if fuente == "⭐ Frecuentes":
            frecuentes_list = obtener_ejercicios_frecuentes()
            if grupo_sel_en:
                ejs_disponibles = sorted([
                    ej for ej in frecuentes_list
                    if grupo_sel_en in biblioteca_completa.get(ej, {}).get("primaryMuscles", [])
                ])
            else:
                ejs_disponibles = sorted(frecuentes_list)
        else:
            if grupo_sel_en:
                ejs_disponibles = sorted([
                    n for n, info in biblioteca_completa.items()
                    if grupo_sel_en in info.get("primaryMuscles", [])
                ])
            else:
                ejs_disponibles = sorted(biblioteca_completa.keys())

        if not ejs_disponibles:
            st.warning("No hay ejercicios con ese filtro.")
        else:
            st.caption(f"{len(ejs_disponibles)} ejercicios")

            # Mantener última selección si sigue disponible
            ultimo_valido = (
                st.session_state.ultimo_ej_sel
                if st.session_state.ultimo_ej_sel in ejs_disponibles
                else ejs_disponibles[0]
            )
            idx_ultimo = ejs_disponibles.index(ultimo_valido) if ultimo_valido in ejs_disponibles else 0

            ej_sel = st.selectbox(
                "Ejercicio",
                ejs_disponibles,
                index=idx_ultimo,
                key="sel_ejercicio_main",
                label_visibility="collapsed",
            )
            # Guardar selección actual (no resetear al agregar)
            st.session_state.ultimo_ej_sel = ej_sel

            # Preview del ejercicio seleccionado
            if ej_sel:
                info_sel = biblioteca_completa.get(ej_sel, {})
                if info_sel.get("url"):
                    st.image(info_sel["url"], use_container_width=True)
                musculos_txt = ", ".join([m_es(m) for m in info_sel.get("primaryMuscles", [])])
                nivel_txt    = info_sel.get("level", "").title()
                equipo_txt   = info_sel.get("equipment", "").title()
                if musculos_txt: st.caption(f"💪 {musculos_txt}")
                if nivel_txt:    st.caption(f"📊 {nivel_txt}  |  🔧 {equipo_txt}")

                # Botón de agregar principal
                if st.button(
                    f"➕ Agregar a la rutina",
                    use_container_width=True,
                    type="primary",
                    disabled=not nombre_input.strip(),
                    help="Escribe el nombre de la rutina primero" if not nombre_input.strip() else "",
                ):
                    ok = agregar_ejercicio_wip(ej_sel)
                    if ok:
                        st.toast(f"✅ {ej_sel} agregado")
                    st.rerun()

    # ─────────────────────────────────────────────────────────
    # COLUMNA DERECHA — Rutina en construcción (tarjetas en vivo)
    # ─────────────────────────────────────────────────────────
    with col_rutina:
        st.subheader("📋 Tu rutina")

        wip = st.session_state.rutina_wip

        if not wip:
            st.markdown(
                "<div style='color:#555;font-size:14px;padding:20px;text-align:center;"
                "border:1px dashed #333;border-radius:10px;margin-top:8px'>"
                "Los ejercicios que agregues aparecerán aquí</div>",
                unsafe_allow_html=True,
            )
        else:
            # ── Undo buffer ──────────────────────────────────
            undo = st.session_state.undo_buffer
            if undo and (time.time() - undo["ts"]) < 8:
                col_u1, col_u2 = st.columns([3, 1])
                col_u1.warning(f"🗑️ **{undo['ejercicio']['ejercicio']}** eliminado")
                if col_u2.button("↩️ Deshacer", use_container_width=True):
                    pos  = min(undo["pos"], len(st.session_state.rutina_wip))
                    st.session_state.rutina_wip.insert(pos, undo["ejercicio"])
                    st.session_state.undo_buffer = None
                    autoguardar()
                    st.rerun()
            elif undo:
                st.session_state.undo_buffer = None  # Expiró

            # ── Tarjetas de ejercicios ────────────────────────
            for i, item in enumerate(wip):
                with st.container(border=True):
                    row_img, row_info = st.columns([1, 3])

                    # Thumbnail
                    with row_img:
                        if item.get("url"):
                            st.image(item["url"], use_container_width=True)
                        else:
                            st.markdown("🏋️", unsafe_allow_html=False)

                    # Info + controles
                    with row_info:
                        musculos_txt = ", ".join([m_es(m) for m in item.get("musculos", [])])
                        st.markdown(f"**{item['ejercicio']}**")
                        if musculos_txt:
                            st.caption(musculos_txt)

                        # ── Botones rápidos de series ─────────
                        st.caption("Series:")
                        bc1, bc2, bc3, bc4, bc5, bc_plus, bc_num = st.columns([1,1,1,1,1,1,2])
                        for btn_col, val in zip([bc1,bc2,bc3,bc4,bc5],[2,3,4,5,6]):
                            if btn_col.button(
                                str(val),
                                key=f"ser_{i}_{val}",
                                use_container_width=True,
                                type="primary" if item["series"] == val else "secondary",
                            ):
                                set_series_wip(i, val)
                                st.rerun()
                        if bc_plus.button("＋", key=f"ser_plus_{i}", use_container_width=True):
                            set_series_wip(i, item["series"] + 1)
                            st.rerun()
                        # Número editable como fallback
                        nuevo_val = bc_num.number_input(
                            "s",
                            min_value=1, max_value=20,
                            value=item["series"],
                            key=f"ser_num_{i}",
                            label_visibility="collapsed",
                        )
                        if nuevo_val != item["series"]:
                            set_series_wip(i, nuevo_val)
                            st.rerun()

                        # ── Controles de posición + eliminar ──
                        ca, cb, cc = st.columns([1, 1, 1])
                        if ca.button("↑", key=f"up_{i}", use_container_width=True,
                                     disabled=(i == 0)):
                            mover_ejercicio_wip(i, -1)
                            st.rerun()
                        if cb.button("↓", key=f"down_{i}", use_container_width=True,
                                     disabled=(i == len(wip) - 1)):
                            mover_ejercicio_wip(i, +1)
                            st.rerun()
                        if cc.button("✕", key=f"del_{i}", use_container_width=True):
                            eliminar_ejercicio_wip(i)
                            st.rerun()

            # ── Volumen estimado en vivo ──────────────────────
            st.divider()
            total_ej, total_ser, por_musculo = calcular_volumen_estimado()

            col_v1, col_v2 = st.columns(2)
            col_v1.metric("Ejercicios", total_ej)
            col_v2.metric("Series totales", total_ser)

            if por_musculo:
                st.markdown("**Distribución por músculo:**")
                max_ser = max(por_musculo.values()) if por_musculo else 1
                for musculo, series in sorted(por_musculo.items(), key=lambda x: -x[1]):
                    pct  = series / max_ser
                    warn = " ⚠️" if series < 2 else ""
                    col_lbl, col_bar, col_num = st.columns([2, 3, 1])
                    col_lbl.caption(musculo)
                    col_bar.progress(pct)
                    col_num.caption(f"**{series}**{warn}")

            # ── Estado de guardado ────────────────────────────
            if nombre_input.strip() and wip:
                ts = st.session_state.guardado_ts
                if ts > 0:
                    hace = int(time.time() - ts)
                    if hace < 10:
                        st.caption("✅ Guardado automáticamente")
                    else:
                        st.caption(f"💾 Último guardado hace {hace}s")
                else:
                    # Primer guardado al finalizar
                    if st.button("💾 Guardar rutina", use_container_width=True, type="primary"):
                        persistir_rutina_db(nombre_input.strip(), wip)
                        st.session_state.guardado_ts = time.time()
                        st.toast(f"✅ Rutina '{nombre_input}' guardada")
                        st.rerun()

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

                # Lista de ejercicios con thumbnail
                for _, fila in ejs_rutina.iterrows():
                    info = biblioteca_completa.get(fila['ejercicio'], {})
                    ci, cn = st.columns([1, 4])
                    if info.get("url"):
                        ci.image(info["url"], use_container_width=True)
                    musculos = ", ".join([m_es(m) for m in info.get("primaryMuscles", [])])
                    cn.markdown(f"**{fila['ejercicio']}**")
                    cn.caption(f"{fila['series_planificadas']} series  ·  {musculos}")

                st.divider()
                col_ed, col_del_r = st.columns(2)

                # ── Cargar para editar ────────────────────────
                if col_ed.button("✏️ Editar", key=f"edit_{nombre_r}", use_container_width=True):
                    st.session_state.rutina_wip        = cargar_rutina_db(nombre_r)
                    st.session_state.rutina_wip_nombre = nombre_r
                    st.session_state.editando_rutina   = nombre_r
                    st.session_state.guardado_ts       = time.time()
                    st.toast(f"✏️ Editando: {nombre_r}")
                    # Cambiar a la tab de creación
                    st.rerun()

                # ── Eliminar rutina completa ──────────────────
                confirm_key = f"confirm_del_r_{nombre_r}"
                if confirm_key not in st.session_state:
                    st.session_state[confirm_key] = False

                if not st.session_state[confirm_key]:
                    if col_del_r.button("🗑️ Eliminar", key=f"del_r_{nombre_r}", use_container_width=True):
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