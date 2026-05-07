import streamlit as st
import sqlite3
import pandas as pd
import altair as alt
from datetime import datetime, date, timedelta

conn = sqlite3.connect("gym_data.db", check_same_thread=False)
c    = conn.cursor()

# ── Tabla de metas ────────────────────────────────────────────────
c.execute("""CREATE TABLE IF NOT EXISTS metas (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ejercicio       TEXT NOT NULL,
    tipo            TEXT NOT NULL,  -- 'peso' | 'reps' | 'volumen'
    valor_objetivo  REAL NOT NULL,
    fecha_limite    DATE NOT NULL,
    fecha_creacion  DATE DEFAULT (DATE('now')),
    completada      INTEGER DEFAULT 0
)""")
conn.commit()

# ── Helpers ───────────────────────────────────────────────────────
def valor_actual(ejercicio, tipo):
    """Retorna el valor actual del usuario para ese ejercicio y tipo de meta."""
    if tipo == "peso":
        row = c.execute(
            "SELECT MAX(peso) FROM entreno WHERE ejercicio=?", (ejercicio,)
        ).fetchone()
        return float(row[0]) if row and row[0] else 0.0
    elif tipo == "reps":
        row = c.execute(
            "SELECT MAX(reps) FROM entreno WHERE ejercicio=?", (ejercicio,)
        ).fetchone()
        return float(row[0]) if row and row[0] else 0.0
    elif tipo == "volumen":
        row = c.execute(
            "SELECT MAX(peso*reps) FROM entreno WHERE ejercicio=?", (ejercicio,)
        ).fetchone()
        return float(row[0]) if row and row[0] else 0.0
    return 0.0

def valor_inicial(ejercicio, tipo, fecha_creacion):
    """Valor que tenía el usuario cuando creó la meta."""
    if tipo == "peso":
        row = c.execute(
            "SELECT MAX(peso) FROM entreno WHERE ejercicio=? AND DATE(fecha)<=?",
            (ejercicio, fecha_creacion)
        ).fetchone()
    elif tipo == "reps":
        row = c.execute(
            "SELECT MAX(reps) FROM entreno WHERE ejercicio=? AND DATE(fecha)<=?",
            (ejercicio, fecha_creacion)
        ).fetchone()
    elif tipo == "volumen":
        row = c.execute(
            "SELECT MAX(peso*reps) FROM entreno WHERE ejercicio=? AND DATE(fecha)<=?",
            (ejercicio, fecha_creacion)
        ).fetchone()
    else:
        return 0.0
    return float(row[0]) if row and row[0] else 0.0

def calcular_ritmo(val_inicial, val_actual, val_objetivo, fecha_creacion, fecha_limite):
    """
    Calcula si el usuario va en buen ritmo para cumplir la meta.
    Retorna: pct_completado, pct_tiempo_usado, en_ritmo (bool), proyeccion_fecha
    """
    hoy = date.today()
    try:
        f_ini  = datetime.strptime(fecha_creacion, "%Y-%m-%d").date() if isinstance(fecha_creacion, str) else fecha_creacion
        f_lim  = datetime.strptime(fecha_limite,   "%Y-%m-%d").date() if isinstance(fecha_limite,   str) else fecha_limite
    except Exception:
        return 0.0, 0.0, False, None

    dias_totales   = max((f_lim - f_ini).days, 1)
    dias_pasados   = max((hoy   - f_ini).days, 0)
    recorrido_obj  = val_objetivo - val_inicial

    if recorrido_obj <= 0:
        pct_completado = 100.0 if val_actual >= val_objetivo else 0.0
    else:
        pct_completado = min(100.0, max(0.0,
            ((val_actual - val_inicial) / recorrido_obj) * 100
        ))

    pct_tiempo = min(100.0, (dias_pasados / dias_totales) * 100)

    # Proyección: si sigue al ritmo actual, ¿cuándo llegaría?
    proyeccion = None
    if dias_pasados > 0 and (val_actual - val_inicial) > 0:
        ritmo_diario = (val_actual - val_inicial) / dias_pasados
        dias_para_meta = (val_objetivo - val_actual) / ritmo_diario
        if dias_para_meta > 0:
            proyeccion = hoy + timedelta(days=int(dias_para_meta))

    en_ritmo = pct_completado >= pct_tiempo * 0.85  # 15% de tolerancia

    return pct_completado, pct_tiempo, en_ritmo, proyeccion

def etiqueta_tipo(tipo):
    return {"peso": "Peso máximo (lb)", "reps": "Reps máximas", "volumen": "Volumen (lb×reps)"}.get(tipo, tipo)

# ── Obtener ejercicios con historial ─────────────────────────────
ejercicios_historial = [r[0] for r in c.execute(
    "SELECT DISTINCT ejercicio FROM entreno ORDER BY ejercicio"
).fetchall()]

# También incluir custom
ejercicios_custom = [r[0] for r in c.execute(
    "SELECT nombre FROM ejercicios_custom ORDER BY nombre"
).fetchall()]

todos_ejercicios = sorted(set(ejercicios_historial + ejercicios_custom))

# ════════════════════════════════════════════════════════════════
# UI PRINCIPAL
# ════════════════════════════════════════════════════════════════
st.title("🎯 Mis Metas")

tab_activas, tab_nueva, tab_completadas = st.tabs(["🔥 Activas", "➕ Nueva Meta", "✅ Completadas"])

# ════════════════════════════════════════════════════════════════
# TAB 1 — METAS ACTIVAS
# ════════════════════════════════════════════════════════════════
with tab_activas:
    metas = c.execute(
        """SELECT id, ejercicio, tipo, valor_objetivo, fecha_limite, fecha_creacion
           FROM metas WHERE completada=0 ORDER BY fecha_limite ASC"""
    ).fetchall()

    if not metas:
        st.info("No tienes metas activas. ¡Crea una en la pestaña '➕ Nueva Meta'!")
    else:
        hoy = date.today()

        for meta in metas:
            mid, ejercicio, tipo, val_obj, f_lim_str, f_cre_str = meta

            val_act  = valor_actual(ejercicio, tipo)
            val_ini  = valor_inicial(ejercicio, tipo, f_cre_str)
            pct_comp, pct_tiempo, en_ritmo, proyeccion = calcular_ritmo(
                val_ini, val_act, val_obj, f_cre_str, f_lim_str
            )

            try:
                f_lim = datetime.strptime(f_lim_str, "%Y-%m-%d").date()
                dias_restantes = (f_lim - hoy).days
            except Exception:
                dias_restantes = 0

            # Color según estado
            if pct_comp >= 100:
                color_border = "#22c55e"
                estado_txt   = "🎉 ¡META CUMPLIDA!"
                estado_col   = "success"
            elif dias_restantes < 0:
                color_border = "#ef4444"
                estado_txt   = "⏰ Venció"
                estado_col   = "error"
            elif en_ritmo:
                color_border = "#3b82f6"
                estado_txt   = "✅ En buen ritmo"
                estado_col   = "info"
            else:
                color_border = "#f59e0b"
                estado_txt   = "⚠️ Necesitas acelerar"
                estado_col   = "warning"

            with st.container(border=True):
                # Header
                ch1, ch2 = st.columns([3, 1])
                ch1.markdown(f"**{ejercicio}**")
                ch1.caption(f"{etiqueta_tipo(tipo)} → **{val_obj:.1f}**")

                if dias_restantes >= 0:
                    ch2.metric("Días", dias_restantes, label_visibility="visible")
                else:
                    ch2.markdown(f"<div style='color:#ef4444;font-weight:700;text-align:right'>Venció</div>",
                                 unsafe_allow_html=True)

                # Barra de progreso del objetivo
                st.progress(min(pct_comp / 100, 1.0))

                # Métricas en línea
                cm1, cm2, cm3 = st.columns(3)
                cm1.metric("Actual",    f"{val_act:.1f}")
                cm2.metric("Objetivo",  f"{val_obj:.1f}")
                cm3.metric("Progreso",  f"{pct_comp:.0f}%")

                # Estado y proyección
                if estado_col == "success":
                    st.success(estado_txt)
                elif estado_col == "error":
                    st.error(estado_txt)
                elif estado_col == "info":
                    st.info(estado_txt)
                else:
                    st.warning(estado_txt)

                if proyeccion and pct_comp < 100:
                    if proyeccion <= f_lim:
                        st.caption(f"📅 Proyección: llegarías el **{proyeccion.strftime('%d/%m/%Y')}** ✅")
                    else:
                        st.caption(f"📅 Al ritmo actual llegarías el **{proyeccion.strftime('%d/%m/%Y')}** — después del límite")

                # Gráfica mini de evolución
                df_ev = pd.read_sql_query(
                    """SELECT DATE(fecha) as dia,
                              MAX(CASE WHEN ? = 'peso' THEN peso
                                       WHEN ? = 'reps' THEN reps
                                       ELSE peso*reps END) as val
                       FROM entreno WHERE ejercicio=?
                       GROUP BY dia ORDER BY dia""",
                    conn, params=(tipo, tipo, ejercicio)
                )
                if not df_ev.empty and len(df_ev) > 1:
                    df_ev['dia_dt'] = pd.to_datetime(df_ev['dia'])
                    df_ev['dia_str'] = df_ev['dia_dt'].dt.strftime('%d/%m')

                    linea = alt.Chart(df_ev).mark_line(
                        color='#3b82f6', strokeWidth=2,
                        point=alt.OverlayMarkDef(color='#3b82f6', size=40)
                    ).encode(
                        x=alt.X('dia_dt:T', title=None, axis=alt.Axis(format='%d/%m', labelAngle=-30)),
                        y=alt.Y('val:Q',    title=None,  scale=alt.Scale(zero=False)),
                        tooltip=[alt.Tooltip('dia_str:N', title='Fecha'),
                                 alt.Tooltip('val:Q', format='.1f')]
                    )
                    # Línea de meta como referencia
                    ref = alt.Chart(pd.DataFrame({'y': [val_obj]})).mark_rule(
                        color='#22c55e', strokeDash=[6, 3], strokeWidth=1.5
                    ).encode(y='y:Q')

                    st.altair_chart((linea + ref).properties(height=130),
                                   use_container_width=True)
                    st.caption("🟢 Línea = objetivo")

                # Acciones
                ca, cb = st.columns(2)
                if pct_comp >= 100:
                    if ca.button("🏆 Marcar completada", key=f"done_{mid}", use_container_width=True, type="primary"):
                        c.execute("UPDATE metas SET completada=1 WHERE id=?", (mid,))
                        conn.commit()
                        st.toast("🎉 ¡Felicitaciones! Meta completada.")
                        st.rerun()
                if cb.button("🗑️ Eliminar", key=f"del_meta_{mid}", use_container_width=True):
                    c.execute("DELETE FROM metas WHERE id=?", (mid,))
                    conn.commit()
                    st.toast("Meta eliminada")
                    st.rerun()

# ════════════════════════════════════════════════════════════════
# TAB 2 — CREAR NUEVA META
# ════════════════════════════════════════════════════════════════
with tab_nueva:
    st.subheader("Definir nueva meta")

    if not todos_ejercicios:
        st.warning("Necesitas tener al menos un ejercicio en tus rutinas para crear una meta.")
        st.stop()

    # Buscar ejercicio
    busq_meta = st.text_input("Buscar ejercicio", placeholder="Escribe para filtrar...",
                               label_visibility="collapsed", key="busq_meta")
    ejs_filtrados = [e for e in todos_ejercicios if busq_meta.lower() in e.lower()] if busq_meta else todos_ejercicios

    ej_meta = st.selectbox("Ejercicio", ejs_filtrados, label_visibility="collapsed", key="ej_meta_sel")

    tipo_meta = st.radio(
        "Tipo de meta",
        ["peso", "reps", "volumen"],
        horizontal=True,
        format_func=etiqueta_tipo,
        key="tipo_meta_radio",
    )

    # Mostrar valor actual como referencia
    val_ahora = valor_actual(ej_meta, tipo_meta)
    if val_ahora > 0:
        st.caption(f"Tu {etiqueta_tipo(tipo_meta)} actual en **{ej_meta}**: **{val_ahora:.1f}**")
        valor_sugerido = val_ahora * 1.10  # +10% como sugerencia
    else:
        st.caption(f"Sin datos previos de {ej_meta}")
        valor_sugerido = 0.0

    valor_obj = st.number_input(
        f"Objetivo ({etiqueta_tipo(tipo_meta)})",
        min_value=0.0,
        value=round(valor_sugerido, 1),
        step=2.5 if tipo_meta == "peso" else 1.0,
        format="%.1f",
    )

    # Validación rápida
    if valor_obj > 0 and val_ahora > 0:
        diferencia = valor_obj - val_ahora
        if diferencia <= 0:
            st.warning("⚠️ El objetivo debe ser mayor a tu valor actual.")
        else:
            pct_aumento = (diferencia / val_ahora) * 100
            st.caption(f"Eso es un aumento de **{diferencia:.1f}** ({pct_aumento:.0f}% de mejora)")

    # Fecha límite con sugerencias rápidas
    st.caption("Fecha límite:")
    fc1, fc2, fc3, fc4 = st.columns(4)
    hoy_d = date.today()
    if fc1.button("1 mes",  key="f1m", use_container_width=True):
        st.session_state.fecha_meta_sel = hoy_d + timedelta(days=30)
    if fc2.button("3 meses", key="f3m", use_container_width=True):
        st.session_state.fecha_meta_sel = hoy_d + timedelta(days=90)
    if fc3.button("6 meses", key="f6m", use_container_width=True):
        st.session_state.fecha_meta_sel = hoy_d + timedelta(days=180)
    if fc4.button("1 año",  key="f1a", use_container_width=True):
        st.session_state.fecha_meta_sel = hoy_d + timedelta(days=365)

    if "fecha_meta_sel" not in st.session_state:
        st.session_state.fecha_meta_sel = hoy_d + timedelta(days=90)

    fecha_lim = st.date_input(
        "o elige manualmente",
        value=st.session_state.fecha_meta_sel,
        min_value=hoy_d + timedelta(days=1),
        label_visibility="collapsed",
        key="fecha_meta_input",
    )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    puede_guardar = (
        ej_meta and
        valor_obj > 0 and
        (val_ahora == 0 or valor_obj > val_ahora)
    )

    if st.button("🎯 Crear meta", use_container_width=True,
                 type="primary", disabled=not puede_guardar):
        c.execute(
            """INSERT INTO metas (ejercicio, tipo, valor_objetivo, fecha_limite, fecha_creacion)
               VALUES (?,?,?,?,?)""",
            (ej_meta, tipo_meta, valor_obj, fecha_lim.isoformat(), hoy_d.isoformat())
        )
        conn.commit()
        st.toast(f"🎯 Meta creada: {ej_meta} → {valor_obj:.1f} ({etiqueta_tipo(tipo_meta)})")
        st.rerun()

# ════════════════════════════════════════════════════════════════
# TAB 3 — METAS COMPLETADAS
# ════════════════════════════════════════════════════════════════
with tab_completadas:
    completadas = c.execute(
        """SELECT ejercicio, tipo, valor_objetivo, fecha_limite, fecha_creacion
           FROM metas WHERE completada=1 ORDER BY fecha_limite DESC"""
    ).fetchall()

    if not completadas:
        st.info("Aún no has completado ninguna meta. ¡Tú puedes! 💪")
    else:
        st.success(f"🏆 Has completado **{len(completadas)}** meta{'s' if len(completadas) > 1 else ''}!")
        for ej, tipo, val_obj, f_lim, f_cre in completadas:
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                c1.markdown(f"✅ **{ej}**")
                c1.caption(f"{etiqueta_tipo(tipo)}: {val_obj:.1f}")
                c2.caption(f"Límite: {f_lim}")