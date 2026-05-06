import streamlit as st
import sqlite3
import pandas as pd
import time
import api_utils
import streamlit.components.v1 as components
from datetime import datetime

# ─── CONEXIÓN ─────────────────────────────────────────────────────
conn = sqlite3.connect("gym_data.db", check_same_thread=False)
c    = conn.cursor()

biblioteca_completa = api_utils.cargar_biblioteca_completa()
biblioteca_visual   = {k: v["url"] for k, v in biblioteca_completa.items()}

# ─── HELPERS ──────────────────────────────────────────────────────
def format_time(seconds):
    mins, secs = divmod(int(seconds), 60)
    return f"{mins:02d}:{secs:02d}"

def reproducir_alarma():
    """Sonido suave tipo 3 beeps usando Web Audio API."""
    js_code = """
    <script>
    (function() {
        var ctx = new (window.AudioContext || window.webkitAudioContext)();
        function beep(freq, start, dur, vol) {
            var o = ctx.createOscillator();
            var g = ctx.createGain();
            o.connect(g); g.connect(ctx.destination);
            o.frequency.value = freq;
            o.type = 'sine';
            g.gain.setValueAtTime(0, ctx.currentTime + start);
            g.gain.linearRampToValueAtTime(vol, ctx.currentTime + start + 0.05);
            g.gain.linearRampToValueAtTime(0, ctx.currentTime + start + dur);
            o.start(ctx.currentTime + start);
            o.stop(ctx.currentTime + start + dur + 0.1);
        }
        beep(880, 0.0, 0.18, 0.3);
        beep(660, 0.22, 0.18, 0.2);
        beep(880, 0.44, 0.28, 0.25);
    })();
    </script>
    """
    st.components.v1.html(js_code, height=0)

def obtener_ultimo_registro(ejercicio):
    """Último peso y reps registrados para el ejercicio."""
    row = c.execute(
        "SELECT peso, reps FROM entreno WHERE ejercicio = ? ORDER BY fecha DESC LIMIT 1",
        (ejercicio,)
    ).fetchone()
    return row  # (peso, reps) o None

def obtener_record_personal(ejercicio):
    """Retorna (max_peso, max_volumen) histórico."""
    max_peso = c.execute(
        "SELECT MAX(peso) FROM entreno WHERE ejercicio = ?", (ejercicio,)
    ).fetchone()[0] or 0

    max_vol_row = c.execute(
        "SELECT (peso * reps) as vol FROM entreno WHERE ejercicio = ? ORDER BY vol DESC LIMIT 1",
        (ejercicio,)
    ).fetchone()
    max_vol = max_vol_row[0] if max_vol_row else 0
    return (float(max_peso), float(max_vol))

def revisar_pr(ejercicio, peso, reps):
    """Devuelve lista de mensajes de PR rotos."""
    pr_peso, pr_vol = obtener_record_personal(ejercicio)
    prs = []
    if peso > pr_peso:
        prs.append(f"🏆 ¡PR de PESO en {ejercicio}!  {peso:.1f} lb")
    if (peso * reps) > pr_vol:
        prs.append(f"🏆 ¡PR de VOLUMEN en {ejercicio}!  {peso:.1f} × {reps} = {peso*reps:.0f}")
    return prs

def obtener_ejercicios_en_rutinas():
    """Ejercicios que ya existen en alguna rutina guardada."""
    rows = c.execute("SELECT DISTINCT ejercicio FROM rutinas ORDER BY ejercicio").fetchall()
    return [r[0] for r in rows]

def generar_etiquetas_series(tipos):
    """
    ['N','W','N','D','N','D'] → ['1','W','2','D','3','D']
    Las normales se numeran secuencialmente.
    """
    etiquetas  = []
    contador_n = 0
    for t in tipos:
        if t == "N":
            contador_n += 1
            etiquetas.append(str(contador_n))
        else:
            etiquetas.append(t)
    return etiquetas

# ─── ESTADO DE SESIÓN ─────────────────────────────────────────────
defaults = {
    "timer_start":      None,
    "ejecutando":       False,
    "sesion_activa_id": None,
    "sesion_rutina":    None,
    "mostrar_notas":    False,
    "duracion_ultima":  0,
    # series_data: {eid: [{"tipo":"N"|"W"|"D", "peso":float, "reps":int, "ok":bool}]}
    "series_data":      {},
    # timer por ejercicio: {eid: unix_timestamp_fin}
    "timer_fin":        {},
    "timer_ej_nombre":  {},
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─── TÍTULO ───────────────────────────────────────────────────────
st.title("Entrenar")

# ─── CARGAR RUTINAS ───────────────────────────────────────────────
df_rutinas_nombres = pd.read_sql_query(
    "SELECT DISTINCT nombre_rutina FROM rutinas", conn
)

if df_rutinas_nombres.empty:
    st.info("Crea una rutina en 'Crear Rutinas' para empezar.")
    st.stop()

nombres = df_rutinas_nombres['nombre_rutina'].tolist()

# ══════════════════════════════════════════════════════════════════
# PANTALLA A — Seleccionar rutina
# ══════════════════════════════════════════════════════════════════
if not st.session_state.ejecutando:

    # Limpiar estado de sesión anterior
    st.session_state.series_data    = {}
    st.session_state.timer_fin      = {}
    st.session_state.timer_ej_nombre = {}

    st.subheader("Selecciona la rutina de hoy")

    for nombre in nombres:
        col_nombre, col_btn = st.columns([3, 1])
        col_nombre.markdown(f"### 🏋️ {nombre}")

        ejercicios_preview = pd.read_sql_query(
            "SELECT ejercicio, series_planificadas FROM rutinas WHERE nombre_rutina = ?",
            conn, params=(nombre,)
        )
        resumen = " · ".join(
            f"{r['ejercicio']} ({r['series_planificadas']}s)"
            for _, r in ejercicios_preview.iterrows()
        )
        col_nombre.caption(resumen[:130] + ("…" if len(resumen) > 130 else ""))

        if col_btn.button("▶ Iniciar", key=f"start_rutina_{nombre}", use_container_width=True):
            ahora = datetime.now().isoformat()
            c.execute(
                "INSERT INTO sesiones (nombre_rutina, inicio) VALUES (?, ?)",
                (nombre, ahora)
            )
            conn.commit()
            st.session_state.sesion_activa_id = c.lastrowid
            st.session_state.sesion_rutina    = nombre
            st.session_state.timer_start      = time.time()
            st.session_state.ejecutando       = True

            # Pre-cargar series con valores de la última sesión
            ejercicios_ini = pd.read_sql_query(
                "SELECT id, ejercicio, series_planificadas FROM rutinas WHERE nombre_rutina = ?",
                conn, params=(nombre,)
            )
            for _, row in ejercicios_ini.iterrows():
                ult = obtener_ultimo_registro(row['ejercicio'])
                p   = float(ult[0]) if ult else 0.0
                r_v = int(ult[1])   if ult else 0
                st.session_state.series_data[row['id']] = [
                    {"tipo": "N", "peso": p, "reps": r_v, "ok": False}
                    for _ in range(row['series_planificadas'])
                ]
            st.rerun()

# ══════════════════════════════════════════════════════════════════
# PANTALLA B — Rutina en curso
# ══════════════════════════════════════════════════════════════════
else:
    rutina_nombre = st.session_state.sesion_rutina
    elapsed       = time.time() - st.session_state.timer_start

    # ── Barra superior ──────────────────────────────────────────
    col_info, col_upd, col_stop = st.columns([3, 1, 1])
    col_info.metric("⏱ Tiempo", format_time(elapsed))
    col_info.caption(f"Entrenando: **{rutina_nombre}**")

    if col_upd.button("Actualizar Temporizador", help="Actualizar tiempo", use_container_width=True):
        st.rerun()

    if col_stop.button("Terminar el entrenamiento", use_container_width=True, type="primary"):
        # ── Guardar todas las series con ✅ ──────────────────────
        for eid, series in st.session_state.series_data.items():
            ej_row = c.execute(
                "SELECT ejercicio FROM rutinas WHERE id = ?", (eid,)
            ).fetchone()
            if not ej_row:
                continue
            ej_nombre = ej_row[0]
            for s in series:
                if s["ok"]:
                    prs = revisar_pr(ej_nombre, s["peso"], s["reps"])
                    c.execute(
                        "INSERT INTO entreno (sesion_id, ejercicio, peso, reps) VALUES (?,?,?,?)",
                        (st.session_state.sesion_activa_id, ej_nombre, s["peso"], s["reps"])
                    )
                    for pr_msg in prs:
                        st.toast(pr_msg, icon="🏆")

        fin      = datetime.now().isoformat()
        duracion = elapsed / 60
        c.execute(
            "UPDATE sesiones SET fin = ?, duracion_min = ? WHERE id = ?",
            (fin, duracion, st.session_state.sesion_activa_id)
        )
        conn.commit()

        st.session_state.ejecutando      = False
        st.session_state.mostrar_notas   = True
        st.session_state.duracion_ultima = duracion
        st.session_state.timer_fin       = {}
        st.session_state.timer_ej_nombre = {}
        st.rerun()

    st.divider()

    # ── Cargar ejercicios de la rutina ───────────────────────────
    ejercicios_plan = pd.read_sql_query(
        "SELECT id, ejercicio, series_planificadas FROM rutinas WHERE nombre_rutina = ?",
        conn, params=(rutina_nombre,)
    )

    # ═══════════════════════════════════════════════════════════════
    # CARD por ejercicio
    # ═══════════════════════════════════════════════════════════════
    hay_timer_activo = False  # para hacer auto-refresh una sola vez al final

    for _, row in ejercicios_plan.iterrows():
        eid       = row['id']
        ej_nombre = row['ejercicio']
        ultimo    = obtener_ultimo_registro(ej_nombre)
        peso_prev = float(ultimo[0]) if ultimo else 0.0
        reps_prev = int(ultimo[1])   if ultimo else 0
        pr_peso, pr_vol = obtener_record_personal(ej_nombre)

        # Inicializar series si no existen aún
        if eid not in st.session_state.series_data:
            st.session_state.series_data[eid] = [
                {"tipo": "N", "peso": peso_prev, "reps": reps_prev, "ok": False}
                for _ in range(row['series_planificadas'])
            ]

        series_ej = st.session_state.series_data[eid]

        # ─ Estado del timer de este ejercicio ─────────────────
        timer_fin_ej = st.session_state.timer_fin.get(eid)
        restante_seg = 0
        timer_activo = False

        if timer_fin_ej:
            restante_seg = int(timer_fin_ej - time.time())
            if restante_seg > 0:
                timer_activo     = True
                hay_timer_activo = True
            else:
                # Sonido y limpiar
                reproducir_alarma()
                st.session_state.timer_fin[eid]       = None
                st.session_state.timer_ej_nombre[eid] = None

        # ─ Label del expander ──────────────────────────────────
        label_prev   = f"  ·  Última: {peso_prev:.1f} lb × {reps_prev} reps" if ultimo else ""
        timer_label  = f"  ⏳ {format_time(restante_seg)}" if timer_activo else ""

        with st.expander(
            f"**{ej_nombre}**{label_prev}{timer_label}",
            expanded=True
        ):
            col_img, col_main = st.columns([1, 2])

            # ─ Imagen + PRs ──────────────────────────────────
            with col_img:
                url = biblioteca_visual.get(ej_nombre)
                if url:
                    st.image(url, use_container_width=True)
                if pr_peso > 0:
                    st.caption(f"🏆 PR peso: {pr_peso:.1f} lb")
                    st.caption(f"🏆 PR vol: {pr_vol:.0f}")

            # ─ Controles superiores ──────────────────────────
            with col_main:
                col_del, col_timer_cfg, col_add, col_rm = st.columns(4)

                # Eliminar ejercicio
                if col_del.button("Eliminar serie", key=f"del_{eid}", use_container_width=True):
                    c.execute("DELETE FROM rutinas WHERE id = ?", (eid,))
                    conn.commit()
                    st.session_state.series_data.pop(eid, None)
                    st.session_state.timer_fin.pop(eid, None)
                    st.rerun()

                # Agregar serie
                if col_add.button("➕ Serie", key=f"add_s_{eid}", use_container_width=True):
                    ult2 = obtener_ultimo_registro(ej_nombre)
                    p2   = float(ult2[0]) if ult2 else 0.0
                    r2   = int(ult2[1])   if ult2 else 0
                    st.session_state.series_data[eid].append(
                        {"tipo": "N", "peso": p2, "reps": r2, "ok": False}
                    )
                    st.rerun()

                # Quitar serie
                if col_rm.button("➖ Serie", key=f"rm_s_{eid}", use_container_width=True):
                    if len(st.session_state.series_data[eid]) > 1:
                        st.session_state.series_data[eid].pop()
                        st.rerun()

                # ── Popover de configuración de timer ────────
                with col_timer_cfg.popover("Temporizador", use_container_width=True):
                    t_min_key = f"tmin_{eid}"
                    t_seg_key = f"tseg_{eid}"
                    if t_min_key not in st.session_state:
                        st.session_state[t_min_key] = 2
                    if t_seg_key not in st.session_state:
                        st.session_state[t_seg_key] = 20

                    new_min = st.number_input(
                        "Minutos", 0, 10,
                        value=st.session_state[t_min_key],
                        key=f"ni_min_{eid}"
                    )
                    new_seg = st.number_input(
                        "Segundos", 0, 59,
                        value=st.session_state[t_seg_key],
                        key=f"ni_seg_{eid}"
                    )
                    st.session_state[t_min_key] = new_min
                    st.session_state[t_seg_key] = new_seg

                    total_cfg = new_min * 60 + new_seg
                    st.caption(f"Descanso configurado: {new_min}m {new_seg}s")

                    if st.button("▶ Iniciar ya", key=f"start_timer_btn_{eid}", use_container_width=True):
                        st.session_state.timer_fin[eid]       = time.time() + total_cfg
                        st.session_state.timer_ej_nombre[eid] = ej_nombre
                        st.rerun()

            # ─ Barra de descanso ─────────────────────────────
            if timer_activo:
                total_cfg_disp = (
                    st.session_state.get(f"tmin_{eid}", 2) * 60 +
                    st.session_state.get(f"tseg_{eid}", 20)
                )
                prog = max(0.0, restante_seg / total_cfg_disp) if total_cfg_disp > 0 else 0.0
                m_r, s_r = divmod(restante_seg, 60)
                col_bar, col_cancel = st.columns([4, 1])
                col_bar.info(f"Descansando — **{m_r:02d}:{s_r:02d}** restantes")
                col_bar.progress(prog)
                if col_cancel.button("❌", key=f"cancel_timer_{eid}", help="Cancelar descanso"):
                    st.session_state.timer_fin[eid]       = None
                    st.session_state.timer_ej_nombre[eid] = None
                    st.rerun()

            # ═══════════════════════════════════════════════════
            # TABLA DE SERIES DINÁMICA
            # ═══════════════════════════════════════════════════
            tipos_actuales = [s["tipo"] for s in series_ej]
            etiquetas      = generar_etiquetas_series(tipos_actuales)

            # Cabecera
            h0, h1, h2, h3, h4 = st.columns([1, 2, 2, 2, 1])
            h0.caption("**#**")
            h1.caption("**Tipo**")
            h2.caption("**Peso (lb)**")
            h3.caption("**Reps**")
            h4.caption("**✅**")

            for i, serie in enumerate(series_ej):
                c0, c1, c2, c3, c4 = st.columns([1, 2, 2, 2, 1])

                # Etiqueta
                c0.markdown(f"**`{etiquetas[i]}`**")

                # Tipo
                tipo_sel = c1.selectbox(
                    "tipo",
                    options=["N", "W", "D"],
                    index=["N", "W", "D"].index(serie["tipo"]),
                    key=f"tipo_{eid}_{i}",
                    label_visibility="collapsed",
                    format_func=lambda x: {"N": "Normal", "W": "Calent.", "D": "Dropset"}[x]
                )

                # Peso
                peso_val = c2.number_input(
                    "lb",
                    min_value=0.0, step=2.5,
                    value=float(serie["peso"]),
                    key=f"peso_{eid}_{i}",
                    label_visibility="collapsed"
                )

                # Reps
                reps_val = c3.number_input(
                    "reps",
                    min_value=0, step=1,
                    value=int(serie["reps"]),
                    key=f"reps_{eid}_{i}",
                    label_visibility="collapsed"
                )

                # Checkbox
                ok_prev = serie["ok"]
                ok_val  = c4.checkbox(
                    "ok",
                    value=ok_prev,
                    key=f"ok_{eid}_{i}",
                    label_visibility="collapsed"
                )

                # Guardar cambios en session_state
                series_ej[i]["tipo"] = tipo_sel
                series_ej[i]["peso"] = peso_val
                series_ej[i]["reps"] = reps_val
                series_ej[i]["ok"]   = ok_val

                # Auto-iniciar timer al marcar ✅
                if ok_val and not ok_prev:
                    t_min  = st.session_state.get(f"tmin_{eid}", 2)
                    t_seg  = st.session_state.get(f"tseg_{eid}", 20)
                    total_auto = t_min * 60 + t_seg
                    if total_auto > 0:
                        st.session_state.timer_fin[eid]       = time.time() + total_auto
                        st.session_state.timer_ej_nombre[eid] = ej_nombre
                        hay_timer_activo = True
                    st.rerun()

            # Persistir
            st.session_state.series_data[eid] = series_ej

    # ── Auto-refresh global si hay algún timer activo ────────────
    if hay_timer_activo:
        time.sleep(1)
        st.rerun()

    # ══════════════════════════════════════════════════════════════
    # AGREGAR EJERCICIO EXTRA
    # ══════════════════════════════════════════════════════════════
    st.divider()
    with st.expander("➕ Añadir ejercicio a esta sesión"):

        ejercicios_en_rutinas = obtener_ejercicios_en_rutinas()
        todos_los_grupos      = api_utils.obtener_grupos_musculares()

        TRAD = {
            "abdominals": "Abdominales", "abductors": "Abductores",
            "adductors": "Aductores",    "biceps": "Bíceps",
            "calves": "Pantorrillas",    "chest": "Pecho",
            "forearms": "Antebrazos",    "glutes": "Glúteos",
            "hamstrings": "Isquiotibiales", "lats": "Espalda (Dorsales)",
            "lower back": "Espalda Baja",   "middle back": "Espalda Media",
            "neck": "Cuello",            "quadriceps": "Cuádriceps",
            "shoulders": "Hombros",      "traps": "Trapecios",
            "triceps": "Tríceps",
        }

        tab_sug, tab_todos = st.tabs(["Mis frecuentes", "🔍 Biblioteca completa"])

        # ── TAB 1: Sugeridos ─────────────────────────────────
        with tab_sug:
            if ejercicios_en_rutinas:
                ej_sug    = st.selectbox("Ejercicio", ejercicios_en_rutinas, key="sug_ej")
                url_sug   = biblioteca_visual.get(ej_sug)
                if url_sug:
                    st.image(url_sug, width=130)
                n_ser_sug = st.number_input("Series", min_value=1, value=3, key="sug_ser")

                if st.button("Agregar", key="btn_add_sug", use_container_width=True, type="primary"):
                    c.execute(
                        "INSERT INTO rutinas (nombre_rutina, ejercicio, series_planificadas) VALUES (?,?,?)",
                        (rutina_nombre, ej_sug, n_ser_sug)
                    )
                    conn.commit()
                    new_id = c.execute(
                        "SELECT id FROM rutinas WHERE nombre_rutina=? AND ejercicio=? ORDER BY id DESC LIMIT 1",
                        (rutina_nombre, ej_sug)
                    ).fetchone()[0]
                    ult3 = obtener_ultimo_registro(ej_sug)
                    p3   = float(ult3[0]) if ult3 else 0.0
                    r3   = int(ult3[1])   if ult3 else 0
                    st.session_state.series_data[new_id] = [
                        {"tipo": "N", "peso": p3, "reps": r3, "ok": False}
                        for _ in range(n_ser_sug)
                    ]
                    st.rerun()
            else:
                st.info("Aún no tienes rutinas guardadas. Usa la biblioteca completa.")

        # ── TAB 2: Biblioteca completa con filtro ─────────────
        with tab_todos:
            grupo_es = st.selectbox(
                "Filtrar por músculo",
                ["Todos"] + [TRAD.get(g, g.title()) for g in todos_los_grupos],
                key="add_grupo"
            )
            grupo_en = None
            if grupo_es != "Todos":
                for en, es in TRAD.items():
                    if es == grupo_es:
                        grupo_en = en
                        break

            ejs_filtrados = sorted([
                n for n, info in biblioteca_completa.items()
                if grupo_en is None or grupo_en in info.get("primaryMuscles", [])
            ])
            st.caption(f"{len(ejs_filtrados)} ejercicios")

            ej_nuevo  = st.selectbox("Ejercicio", ejs_filtrados, key="add_ej_nuevo")
            url_nuevo = biblioteca_visual.get(ej_nuevo)
            if url_nuevo:
                st.image(url_nuevo, width=130)

            n_ser_nuevo = st.number_input("Series", min_value=1, value=3, key="add_ser_nuevo")

            if st.button("Agregar", key="btn_add_nuevo", use_container_width=True, type="primary"):
                c.execute(
                    "INSERT INTO rutinas (nombre_rutina, ejercicio, series_planificadas) VALUES (?,?,?)",
                    (rutina_nombre, ej_nuevo, n_ser_nuevo)
                )
                conn.commit()
                new_id2 = c.execute(
                    "SELECT id FROM rutinas WHERE nombre_rutina=? AND ejercicio=? ORDER BY id DESC LIMIT 1",
                    (rutina_nombre, ej_nuevo)
                ).fetchone()[0]
                ult4 = obtener_ultimo_registro(ej_nuevo)
                p4   = float(ult4[0]) if ult4 else 0.0
                r4   = int(ult4[1])   if ult4 else 0
                st.session_state.series_data[new_id2] = [
                    {"tipo": "N", "peso": p4, "reps": r4, "ok": False}
                    for _ in range(n_ser_nuevo)
                ]
                st.rerun()

# ══════════════════════════════════════════════════════════════════
# MODAL DE NOTAS (post-rutina)
# ══════════════════════════════════════════════════════════════════
if st.session_state.get("mostrar_notas", False):

    @st.dialog("🏁 ¡Rutina Completada!")
    def modal_notas():
        dur = st.session_state.get("duracion_ultima", 0)
        st.success(f"⏱ Duración total: **{dur:.1f} minutos**")
        nota = st.text_area(
            "¿Cómo te fue hoy? (opcional)",
            placeholder="Ej: Dormí bien, aumenté peso en press, mucho volumen...",
        )
        if st.button("💾 Guardar y cerrar", use_container_width=True, type="primary"):
            if nota.strip():
                c.execute(
                    "UPDATE sesiones SET notas = ? WHERE id = ?",
                    (nota.strip(), st.session_state.sesion_activa_id)
                )
                conn.commit()
            # Reset completo de sesión
            st.session_state.mostrar_notas    = False
            st.session_state.sesion_activa_id = None
            st.session_state.sesion_rutina    = None
            st.session_state.duracion_ultima  = 0
            st.session_state.series_data      = {}
            st.session_state.timer_fin        = {}
            st.session_state.timer_ej_nombre  = {}
            st.rerun()

    modal_notas()