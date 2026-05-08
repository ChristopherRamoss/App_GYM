import streamlit as st
import sqlite3
import pandas as pd
import time
import api_utils
import streamlit.components.v1 as components
from datetime import datetime, timedelta

# ─── CONEXIÓN ─────────────────────────────────────────────────────
conn = sqlite3.connect("gym_data.db", check_same_thread=False)
c    = conn.cursor()

biblioteca_completa = api_utils.cargar_biblioteca_completa()
biblioteca_visual   = {k: v["url"] for k, v in biblioteca_completa.items()}

# ══════════════════════════════════════════════════════════════════
# CSS — Highlight de series + micro-animaciones
# Solo estilos que Streamlit no puede hacer nativamente
# ══════════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* ── Fila completada: verde suave ── */
.serie-done {
    background: linear-gradient(90deg, #0d2818 0%, #0f2f1a 100%);
    border-left: 3px solid #22c55e;
    border-radius: 6px;
    padding: 4px 8px;
    margin: 2px 0;
    transition: all 0.3s ease;
}
/* ── Fila normal ── */
.serie-pending {
    border-left: 3px solid transparent;
    border-radius: 6px;
    padding: 4px 8px;
    margin: 2px 0;
    transition: all 0.3s ease;
}
/* ── Badge de fatiga ── */
.fatigue-low  { background:#14532d; color:#4ade80; padding:2px 8px; border-radius:12px; font-size:12px; font-weight:600; }
.fatigue-mid  { background:#78350f; color:#fbbf24; padding:2px 8px; border-radius:12px; font-size:12px; font-weight:600; }
.fatigue-high { background:#450a0a; color:#f87171; padding:2px 8px; border-radius:12px; font-size:12px; font-weight:600; }
/* ── Toast personalizado (complementa st.toast) ── */
.mini-toast {
    background: #1a1a2e;
    border: 1px solid #22c55e;
    color: #4ade80;
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 13px;
    display: inline-block;
    margin: 4px 0;
}
/* ── Animación de check ── */
@keyframes checkPop {
    0%   { transform: scale(1); }
    50%  { transform: scale(1.15); }
    100% { transform: scale(1); }
}
.check-pop { animation: checkPop 0.25s ease; }
/* ── Progress del timer más visible ── */
div[data-testid="stProgress"] > div { border-radius: 4px !important; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# SISTEMA DE FATIGA — Heurística pura, sin ML
# ══════════════════════════════════════════════════════════════════
TRAD_MUSCULOS = {
    "abdominals":"Abdominales","abductors":"Abductores","adductors":"Aductores",
    "biceps":"Bíceps","calves":"Pantorrillas","chest":"Pecho",
    "forearms":"Antebrazos","glutes":"Glúteos","hamstrings":"Isquiotibiales",
    "lats":"Dorsales","lower back":"Esp. Baja","middle back":"Esp. Media",
    "neck":"Cuello","quadriceps":"Cuádriceps","shoulders":"Hombros",
    "traps":"Trapecios","triceps":"Tríceps",
}

def calcular_fatiga():
    """
    Heurística de fatiga por grupo muscular.
    Score 0–100 basado en:
      - Frecuencia últimos 7 días (más frecuencia → más fatiga)
      - Recencia (más reciente → más fatiga)
      - Volumen relativo (más volumen → más fatiga)

    Retorna dict: {musculo_es: {"score": int, "nivel": str, "dias": int}}
    """
    hoy = datetime.now()
    hace_7 = (hoy - timedelta(days=7)).isoformat()

    # Ejercicios realizados últimos 7 días con fecha y volumen
    rows = c.execute("""
        SELECT e.ejercicio, DATE(e.fecha) as dia, SUM(e.peso * e.reps) as vol
        FROM entreno e
        WHERE e.fecha >= ?
        GROUP BY e.ejercicio, dia
        ORDER BY dia DESC
    """, (hace_7,)).fetchall()

    if not rows:
        return {}

    # Acumular por músculo
    musculo_data = {}  # {musculo_en: {"dias": set, "vol_total": float, "ultimo_dia": date}}
    for ej_nombre, dia_str, vol in rows:
        info = biblioteca_completa.get(ej_nombre, {})
        for m in info.get("primaryMuscles", []):
            try:
                dia = datetime.strptime(dia_str, "%Y-%m-%d").date()
            except Exception:
                continue
            if m not in musculo_data:
                musculo_data[m] = {"dias": set(), "vol_total": 0.0, "ultimo_dia": dia}
            musculo_data[m]["dias"].add(dia)
            musculo_data[m]["vol_total"] += vol or 0
            if dia > musculo_data[m]["ultimo_dia"]:
                musculo_data[m]["ultimo_dia"] = dia

    if not musculo_data:
        return {}

    # Normalización para score relativo
    max_freq = max(len(d["dias"]) for d in musculo_data.values())
    max_vol  = max(d["vol_total"] for d in musculo_data.values()) or 1

    resultado = {}
    hoy_date  = hoy.date()

    for m, data in musculo_data.items():
        dias_desde_ultimo = (hoy_date - data["ultimo_dia"]).days
        frecuencia        = len(data["dias"])
        vol_norm          = data["vol_total"] / max_vol

        # Recencia: 0 días → 1.0, 7+ días → 0.0
        recencia = max(0.0, 1.0 - dias_desde_ultimo / 7.0)
        # Frecuencia normalizada
        freq_norm = frecuencia / max(max_freq, 1)
        # Score ponderado: recencia pesa más (40%), freq (35%), vol (25%)
        score = int((recencia * 40 + freq_norm * 35 + vol_norm * 25))
        score = min(100, max(0, score))

        if score >= 65:
            nivel = "alto"
        elif score >= 35:
            nivel = "moderado"
        else:
            nivel = "bajo"

        musculo_es = TRAD_MUSCULOS.get(m, m.title())
        resultado[musculo_es] = {
            "score":       score,
            "nivel":       nivel,
            "dias":        dias_desde_ultimo,
            "frecuencia":  frecuencia,
        }

    return resultado

def musculos_recomendados(fatiga_dict):
    """Devuelve lista de grupos musculares con fatiga baja para recomendar hoy."""
    if not fatiga_dict:
        return []
    bajos = [m for m, d in fatiga_dict.items() if d["nivel"] == "bajo"]
    return bajos[:4]

# ─── HELPERS GENERALES ────────────────────────────────────────────
def format_time(seconds):
    mins, secs = divmod(int(seconds), 60)
    return f"{mins:02d}:{secs:02d}"

def reproducir_alarma():
    js = """<script>
    (function(){
        var ctx=new(window.AudioContext||window.webkitAudioContext)();
        function b(f,s,d,v){
            var o=ctx.createOscillator(),g=ctx.createGain();
            o.connect(g);g.connect(ctx.destination);
            o.frequency.value=f;o.type='sine';
            g.gain.setValueAtTime(0,ctx.currentTime+s);
            g.gain.linearRampToValueAtTime(v,ctx.currentTime+s+0.05);
            g.gain.linearRampToValueAtTime(0,ctx.currentTime+s+d);
            o.start(ctx.currentTime+s);o.stop(ctx.currentTime+s+d+0.1);
        }
        b(880,0.0,0.18,0.3);b(660,0.22,0.18,0.2);b(880,0.44,0.28,0.25);
    })();
    </script>"""
    st.components.v1.html(js, height=0)

def obtener_ultimo_registro(ejercicio):
    return c.execute(
        "SELECT peso, reps FROM entreno WHERE ejercicio=? ORDER BY fecha DESC LIMIT 1",
        (ejercicio,)
    ).fetchone()

def obtener_record_personal(ejercicio):
    mp = c.execute("SELECT MAX(peso) FROM entreno WHERE ejercicio=?", (ejercicio,)).fetchone()[0] or 0
    mv = c.execute(
        "SELECT (peso*reps) as v FROM entreno WHERE ejercicio=? ORDER BY v DESC LIMIT 1",
        (ejercicio,)
    ).fetchone()
    return float(mp), float(mv[0]) if mv else 0.0

def revisar_pr(ejercicio, peso, reps):
    pr_p, pr_v = obtener_record_personal(ejercicio)
    out = []
    if peso > pr_p and pr_p > 0:
        out.append(f"🏆 ¡PR de PESO en {ejercicio}! {peso:.1f} lb")
    if peso * reps > pr_v and pr_v > 0:
        out.append(f"🏆 ¡PR de VOLUMEN en {ejercicio}! {peso:.1f}×{reps}={peso*reps:.0f}")
    return out

def guardar_serie_inmediata(sesion_id, ejercicio, peso, reps):
    """Autoguardado: inserta la serie en DB de inmediato al hacer ✅."""
    c.execute(
        "INSERT INTO entreno (sesion_id, ejercicio, peso, reps) VALUES (?,?,?,?)",
        (sesion_id, ejercicio, peso, reps)
    )
    conn.commit()

def construir_tabla_inicial(series_data_ej, peso_prev, reps_prev):
    filas = []
    contador_n = 0
    for s in series_data_ej:
        if s["tipo"] == "N":
            contador_n += 1
            etq = str(contador_n)
        else:
            etq = s["tipo"]
        filas.append({
            "#":         etq,
            "Anterior":  s.get("anterior_str", "—"),
            "Peso (lb)": s["peso"],
            "Reps":      s["reps"],
            "✅":        s["ok"],
        })
    return pd.DataFrame(filas)

def tabla_a_series(df_editado, series_previas):
    series = []
    for i, (_, row) in enumerate(df_editado.iterrows()):
        etq = str(row["#"]).strip().upper()
        tipo = "W" if etq == "W" else ("D" if etq == "D" else "N")
        anterior_str = series_previas[i].get("anterior_str", "—") if i < len(series_previas) else "—"
        series.append({
            "tipo":         tipo,
            "peso":         float(row["Peso (lb)"]),
            "reps":         int(row["Reps"]),
            "ok":           bool(row["✅"]),
            "anterior_str": anterior_str,
            "guardado":     series_previas[i].get("guardado", False) if i < len(series_previas) else False,
        })
    return series

def obtener_ejercicios_en_rutinas():
    rows = c.execute("SELECT DISTINCT ejercicio FROM rutinas ORDER BY ejercicio").fetchall()
    return [r[0] for r in rows]

# ─── SESSION STATE ─────────────────────────────────────────────────
for k, v in {
    "timer_start": None, "ejecutando": False,
    "sesion_activa_id": None, "sesion_rutina": None,
    "mostrar_notas": False, "duracion_ultima": 0,
    "series_data": {}, "timer_fin": {}, "timer_ej_nombre": {},
    "fatiga_cache": None, "fatiga_ts": 0,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─── CARGAR RUTINAS ───────────────────────────────────────────────
df_rutinas_nombres = pd.read_sql_query("SELECT DISTINCT nombre_rutina FROM rutinas", conn)
if df_rutinas_nombres.empty:
    st.info("Crea una rutina en 'Crear Rutinas' para empezar.")
    st.stop()
nombres = df_rutinas_nombres['nombre_rutina'].tolist()

# ══════════════════════════════════════════════════════════════════
# PANTALLA A — Selector de rutina + Panel de fatiga
# ══════════════════════════════════════════════════════════════════
if not st.session_state.ejecutando:
    st.session_state.series_data     = {}
    st.session_state.timer_fin       = {}
    st.session_state.timer_ej_nombre = {}

    st.title("💪 Entrenar")


    st.divider()
    st.subheader("Selecciona la rutina de hoy")

    for nombre in nombres:
        col_nombre, col_btn = st.columns([3, 1])
        col_nombre.markdown(f"### 🏋️ {nombre}")

        ejs_prev = pd.read_sql_query(
            "SELECT ejercicio, series_planificadas FROM rutinas WHERE nombre_rutina=?",
            conn, params=(nombre,)
        )
        resumen = " · ".join(
            f"{r['ejercicio']} ({r['series_planificadas']}s)" for _, r in ejs_prev.iterrows()
        )
        col_nombre.caption(resumen[:130] + ("…" if len(resumen) > 130 else ""))

        if col_btn.button("▶ Iniciar", key=f"start_{nombre}", use_container_width=True):
            ahora = datetime.now().isoformat()
            c.execute("INSERT INTO sesiones (nombre_rutina, inicio) VALUES (?,?)", (nombre, ahora))
            conn.commit()
            st.session_state.sesion_activa_id = c.lastrowid
            st.session_state.sesion_rutina    = nombre
            st.session_state.timer_start      = time.time()
            st.session_state.ejecutando       = True
            # Pre-cargar series con último registro
            for _, row in pd.read_sql_query(
                "SELECT id, ejercicio, series_planificadas FROM rutinas WHERE nombre_rutina=?",
                conn, params=(nombre,)
            ).iterrows():
                ult  = obtener_ultimo_registro(row['ejercicio'])
                p    = float(ult[0]) if ult else 0.0
                r_v  = int(ult[1])   if ult else 0
                ant  = f"{p:.0f} lb × {r_v}" if ult else "—"
                st.session_state.series_data[row['id']] = [
                    {"tipo":"N","peso":p,"reps":r_v,"ok":False,"anterior_str":ant,"guardado":False}
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

    if col_upd.button("🔄 Actualizar", use_container_width=True):
        st.rerun()

    if col_stop.button("🏁 Terminar", use_container_width=True, type="primary"):
        # Solo necesitamos cerrar la sesión — las series ya se guardaron por autoguardado
        fin = datetime.now().isoformat()
        dur = elapsed / 60
        c.execute("UPDATE sesiones SET fin=?,duracion_min=? WHERE id=?",
                  (fin, dur, st.session_state.sesion_activa_id))
        conn.commit()
        # Series sin guardar (por si el usuario no hizo check en algunas)
        series_pendientes = 0
        for eid, slist in st.session_state.series_data.items():
            for s in slist:
                if s["ok"] and not s.get("guardado", False):
                    series_pendientes += 1
        if series_pendientes > 0:
            st.warning(f"⚠️ Hay {series_pendientes} series marcadas que no se guardaron. Verifica.")
        st.session_state.ejecutando      = False
        st.session_state.mostrar_notas   = True
        st.session_state.duracion_ultima = dur
        st.session_state.timer_fin       = {}
        st.rerun()

    st.divider()

    ejercicios_plan = pd.read_sql_query(
        "SELECT id, ejercicio, series_planificadas FROM rutinas WHERE nombre_rutina=?",
        conn, params=(rutina_nombre,)
    )

    hay_timer = False

    for _, row in ejercicios_plan.iterrows():
        eid       = row['id']
        ej_nombre = row['ejercicio']
        ultimo    = obtener_ultimo_registro(ej_nombre)
        peso_prev = float(ultimo[0]) if ultimo else 0.0
        reps_prev = int(ultimo[1])   if ultimo else 0
        pr_peso, pr_vol = obtener_record_personal(ej_nombre)
        ant_str   = f"{peso_prev:.0f} lb × {reps_prev}" if ultimo else "—"

        if eid not in st.session_state.series_data:
            st.session_state.series_data[eid] = [
                {"tipo":"N","peso":peso_prev,"reps":reps_prev,"ok":False,"anterior_str":ant_str,"guardado":False}
                for _ in range(row['series_planificadas'])
            ]

        series_ej = st.session_state.series_data[eid]

        # Estado timer
        timer_fin_ej = st.session_state.timer_fin.get(eid)
        restante_seg = 0
        timer_activo = False
        if timer_fin_ej:
            restante_seg = int(timer_fin_ej - time.time())
            if restante_seg > 0:
                timer_activo = True
                hay_timer    = True
            else:
                reproducir_alarma()
                st.session_state.timer_fin[eid] = None

        # Conteo de series completadas para el label
        n_ok     = sum(1 for s in series_ej if s["ok"])
        n_total  = len(series_ej)
        ok_label = f" ✅ {n_ok}/{n_total}" if n_ok > 0 else ""
        t_label  = f" ⏳ {format_time(restante_seg)}" if timer_activo else ""
        prev_lbl = f" · {ant_str}" if ultimo else ""

        with st.expander(f"**{ej_nombre}**{prev_lbl}{ok_label}{t_label}", expanded=True):

            col_img, col_main = st.columns([1, 2])

            with col_img:
                url = biblioteca_visual.get(ej_nombre)
                if url:
                    st.image(url, use_container_width=True)

            with col_main:
                col_del, col_timer_cfg, col_add, col_rm = st.columns(4)

                if col_del.button("🗑️ Quitar", key=f"del_{eid}", use_container_width=True):
                    c.execute("DELETE FROM rutinas WHERE id=?", (eid,))
                    conn.commit()
                    st.session_state.series_data.pop(eid, None)
                    st.session_state.timer_fin.pop(eid, None)
                    st.rerun()

                if col_add.button("➕ Serie", key=f"add_s_{eid}", use_container_width=True):
                    st.session_state.series_data[eid].append(
                        {"tipo":"N","peso":peso_prev,"reps":reps_prev,"ok":False,"anterior_str":ant_str,"guardado":False}
                    )
                    st.rerun()

                if col_rm.button("➖ Serie", key=f"rm_s_{eid}", use_container_width=True):
                    if len(st.session_state.series_data[eid]) > 1:
                        st.session_state.series_data[eid].pop()
                        st.rerun()

                with col_timer_cfg.popover("⏱️ Timer", use_container_width=True):
                    if f"tmin_{eid}" not in st.session_state: st.session_state[f"tmin_{eid}"] = 2
                    if f"tseg_{eid}" not in st.session_state: st.session_state[f"tseg_{eid}"] = 20
                    new_min = st.number_input("Min", 0, 10, value=st.session_state[f"tmin_{eid}"], key=f"ni_min_{eid}")
                    new_seg = st.number_input("Seg", 0, 59, value=st.session_state[f"tseg_{eid}"], key=f"ni_seg_{eid}")
                    st.session_state[f"tmin_{eid}"] = new_min
                    st.session_state[f"tseg_{eid}"] = new_seg
                    st.caption(f"Descanso: {new_min}m {new_seg}s")
                    if st.button("▶ Iniciar ya", key=f"start_t_{eid}"):
                        st.session_state.timer_fin[eid] = time.time() + new_min * 60 + new_seg
                        st.rerun()

            # ── Timer bar ────────────────────────────────────
            if timer_activo:
                total_t  = st.session_state.get(f"tmin_{eid}", 2) * 60 + st.session_state.get(f"tseg_{eid}", 20)
                prog     = max(0.0, restante_seg / total_t) if total_t > 0 else 0.0
                m_r, s_r = divmod(restante_seg, 60)
                cb, cc   = st.columns([4, 1])
                cb.info(f"😮‍💨 Descansando — **{m_r:02d}:{s_r:02d}** restantes")
                cb.progress(prog)
                if cc.button("❌", key=f"cancel_t_{eid}"):
                    st.session_state.timer_fin[eid] = None
                    st.rerun()

            # ══════════════════════════════════════════════════
            # TABLA DE SERIES con highlight visual
            # ══════════════════════════════════════════════════

            # Render del highlight ANTES del data_editor
            # Mostramos una barra visual de estado sobre la tabla
            if any(s["ok"] for s in series_ej):
                done_count = sum(1 for s in series_ej if s["ok"])
                pct_done   = done_count / len(series_ej)
                st.progress(pct_done, text=f"{done_count} de {len(series_ej)} series completadas")

            # Highlight por filas: generamos HTML indicativo DEBAJO del editor
            # (Streamlit no permite styles en filas de data_editor, pero sí podemos
            #  mostrar un indicador visual claro justo encima con markdown)
            filas_html = ""
            contador_n = 0
            for i, s in enumerate(series_ej):
                if s["tipo"] == "N":
                    contador_n += 1
                    etq = str(contador_n)
                else:
                    etq = s["tipo"]
                if s["ok"]:
                    color_etq = "#22c55e"
                    icon      = "✅"
                elif s["tipo"] == "W":
                    color_etq = "#f59e0b"
                    icon      = ""
                elif s["tipo"] == "D":
                    color_etq = "#a855f7"
                    icon      = ""
                else:
                    color_etq = "#888"
                    icon      = ""
                bg_color = "#14532d" if s["ok"] else "#232323"
                filas_html += (
                    f"<span style='display:inline-block;width:28px;height:28px;"
                    f"background:{bg_color};color:{color_etq};"
                    f"border-radius:6px;text-align:center;line-height:28px;"
                    f"font-weight:700;font-size:13px;margin-right:4px'>{etq}</span>"
                )

            st.markdown(
                f"<div style='margin:4px 0 6px'>{filas_html}</div>",
                unsafe_allow_html=True
            )

            # Data editor principal
            df_series = construir_tabla_inicial(series_ej, peso_prev, reps_prev)
            oks_previos = [s["ok"] for s in series_ej]

            df_editado = st.data_editor(
                df_series,
                key=f"ed_{eid}",
                hide_index=True,
                use_container_width=True,
                column_config={
                    "#": st.column_config.TextColumn(
                        "#", help="Número de serie. W=calentamiento, D=dropset",
                        max_chars=3, width="small"
                    ),
                    "Anterior": st.column_config.TextColumn(
                        "Anterior", disabled=True, width="medium"
                    ),
                    "Peso (lb)": st.column_config.NumberColumn(
                        "Peso (lb)", format="%.1f", step=2.5, min_value=0.0, width="small"
                    ),
                    "Reps": st.column_config.NumberColumn(
                        "Reps", step=1, min_value=0, width="small"
                    ),
                    "✅": st.column_config.CheckboxColumn("✅", width="small"),
                }
            )

            # Sincronizar + AUTOGUARDADO al marcar ✅
            nuevas_series = tabla_a_series(df_editado, series_ej)
            st.session_state.series_data[eid] = nuevas_series

            for i, (nueva, ok_prev) in enumerate(zip(nuevas_series, oks_previos)):
                if nueva["ok"] and not ok_prev:
                    # ── AUTOGUARDADO INMEDIATO ──────────────
                    if st.session_state.sesion_activa_id and not nueva.get("guardado", False):
                        guardar_serie_inmediata(
                            st.session_state.sesion_activa_id,
                            ej_nombre, nueva["peso"], nueva["reps"]
                        )
                        st.session_state.series_data[eid][i]["guardado"] = True

                        # PR check
                        prs = revisar_pr(ej_nombre, nueva["peso"], nueva["reps"])
                        for pr in prs:
                            st.toast(pr, icon="🏆")
                        if not prs:
                            st.toast(f"✅ Serie guardada — {nueva['peso']:.1f} lb × {nueva['reps']} reps")

                    # ── Auto-timer ──────────────────────────
                    t_min = st.session_state.get(f"tmin_{eid}", 2)
                    t_seg = st.session_state.get(f"tseg_{eid}", 20)
                    total = t_min * 60 + t_seg
                    if total > 0:
                        st.session_state.timer_fin[eid] = time.time() + total
                        hay_timer = True
                    st.rerun()

    # ── Auto-refresh si hay timer ─────────────────────────────
    if hay_timer:
        time.sleep(1)
        st.rerun()

    # ══════════════════════════════════════════════════════════════
    # AGREGAR EJERCICIO EXTRA
    # ══════════════════════════════════════════════════════════════
    st.divider()
    with st.expander("➕ Añadir ejercicio a esta sesión"):
        TRAD = {
            "abdominals":"Abdominales","abductors":"Abductores","adductors":"Aductores",
            "biceps":"Bíceps","calves":"Pantorrillas","chest":"Pecho",
            "forearms":"Antebrazos","glutes":"Glúteos","hamstrings":"Isquiotibiales",
            "lats":"Dorsales","lower back":"Esp. Baja","middle back":"Esp. Media",
            "neck":"Cuello","quadriceps":"Cuádriceps","shoulders":"Hombros",
            "traps":"Trapecios","triceps":"Tríceps",
        }
        tab_sug, tab_todos = st.tabs(["⭐ Mis frecuentes", "🔍 Biblioteca"])

        with tab_sug:
            frecuentes = obtener_ejercicios_en_rutinas()
            if frecuentes:
                ej_s = st.selectbox("Ejercicio", frecuentes, key="sug_ej")
                url_s = biblioteca_visual.get(ej_s)
                if url_s: st.image(url_s, width=120)
                n_s = st.number_input("Series", 1, 20, 3, key="sug_ser")
                if st.button("Agregar", key="btn_sug", use_container_width=True, type="primary"):
                    c.execute("INSERT INTO rutinas(nombre_rutina,ejercicio,series_planificadas) VALUES(?,?,?)",
                              (rutina_nombre, ej_s, n_s))
                    conn.commit()
                    nid = c.execute(
                        "SELECT id FROM rutinas WHERE nombre_rutina=? AND ejercicio=? ORDER BY id DESC LIMIT 1",
                        (rutina_nombre, ej_s)
                    ).fetchone()[0]
                    ult = obtener_ultimo_registro(ej_s)
                    p  = float(ult[0]) if ult else 0.0
                    rv = int(ult[1])   if ult else 0
                    st.session_state.series_data[nid] = [
                        {"tipo":"N","peso":p,"reps":rv,"ok":False,"anterior_str":f"{p:.0f} lb × {rv}" if ult else "—","guardado":False}
                        for _ in range(n_s)
                    ]
                    st.rerun()
            else:
                st.info("Usa la biblioteca para agregar ejercicios.")

        with tab_todos:
            grupos = api_utils.obtener_grupos_musculares()
            g_es = st.selectbox("Músculo", ["Todos"] + [TRAD.get(g, g.title()) for g in grupos], key="add_g")
            g_en = next((en for en, es in TRAD.items() if es == g_es), None) if g_es != "Todos" else None
            ejs_f = sorted([n for n, info in biblioteca_completa.items()
                            if g_en is None or g_en in info.get("primaryMuscles", [])])
            st.caption(f"{len(ejs_f)} ejercicios")
            ej_n = st.selectbox("Ejercicio", ejs_f, key="add_ej_n")
            url_n = biblioteca_visual.get(ej_n)
            if url_n: st.image(url_n, width=120)
            n_n = st.number_input("Series", 1, 20, 3, key="add_ser_n")
            if st.button("Agregar", key="btn_add_n", use_container_width=True, type="primary"):
                c.execute("INSERT INTO rutinas(nombre_rutina,ejercicio,series_planificadas) VALUES(?,?,?)",
                          (rutina_nombre, ej_n, n_n))
                conn.commit()
                nid2 = c.execute(
                    "SELECT id FROM rutinas WHERE nombre_rutina=? AND ejercicio=? ORDER BY id DESC LIMIT 1",
                    (rutina_nombre, ej_n)
                ).fetchone()[0]
                ult2 = obtener_ultimo_registro(ej_n)
                p2   = float(ult2[0]) if ult2 else 0.0
                rv2  = int(ult2[1])   if ult2 else 0
                st.session_state.series_data[nid2] = [
                    {"tipo":"N","peso":p2,"reps":rv2,"ok":False,"anterior_str":f"{p2:.0f} lb × {rv2}" if ult2 else "—","guardado":False}
                    for _ in range(n_n)
                ]
                st.rerun()

# ══════════════════════════════════════════════════════════════════
# MODAL NOTAS POST-RUTINA
# ══════════════════════════════════════════════════════════════════
if st.session_state.get("mostrar_notas", False):
    @st.dialog("🏁 ¡Rutina Completada!")
    def modal_notas():
        dur = st.session_state.get("duracion_ultima", 0)
        st.success(f"⏱ Duración: **{dur:.1f} minutos** — ¡Gran trabajo!")
        nota = st.text_area("¿Cómo te fue hoy?",
                            placeholder="Dormí bien, aumenté peso, mucho volumen...")
        if st.button("💾 Cerrar y guardar", use_container_width=True, type="primary"):
            if nota.strip():
                c.execute("UPDATE sesiones SET notas=? WHERE id=?",
                          (nota.strip(), st.session_state.sesion_activa_id))
                conn.commit()
            st.session_state.mostrar_notas    = False
            st.session_state.sesion_activa_id = None
            st.session_state.sesion_rutina    = None
            st.session_state.duracion_ultima  = 0
            st.session_state.series_data      = {}
            st.session_state.timer_fin        = {}
            st.session_state.timer_ej_nombre  = {}
            st.session_state.fatiga_cache     = None  # Forzar recálculo post-entreno
            st.rerun()
    modal_notas()