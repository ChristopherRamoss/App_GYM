import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# ─── CONEXIÓN ─────────────────────────────────────────────────────
conn = sqlite3.connect("gym_data.db", check_same_thread=False)
c    = conn.cursor()

# Asegurar tablas (por si se carga antes que main.py las cree)
c.execute("""CREATE TABLE IF NOT EXISTS perfil (
    id     INTEGER PRIMARY KEY,
    nombre TEXT DEFAULT 'Christopher',
    edad   INTEGER DEFAULT 25
)""")
c.execute("""CREATE TABLE IF NOT EXISTS peso_corporal (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    peso  REAL,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""")
c.execute("INSERT OR IGNORE INTO perfil (id, nombre, edad) VALUES (1, 'Christopher', 25)")
conn.commit()

# ─── CARGAR PERFIL ────────────────────────────────────────────────
perfil = c.execute("SELECT nombre, edad FROM perfil WHERE id = 1").fetchone()
nombre_actual = perfil[0] if perfil else "Christopher"
edad_actual   = perfil[1] if perfil else 25

# ─── UI ───────────────────────────────────────────────────────────
st.title(nombre_actual)

# ══════════════════════════════════════════════════════════════════
# SECCIÓN 1: Datos personales
# ══════════════════════════════════════════════════════════════════
col1, col2 = st.columns(2)

# Obtener peso más reciente
ultimo_peso_row = c.execute(
    "SELECT peso, fecha FROM peso_corporal ORDER BY fecha DESC LIMIT 1"
).fetchone()
peso_display = f"{ultimo_peso_row[0]:.1f} lb" if ultimo_peso_row else "Sin datos"

col1.metric("Peso Actual", peso_display)
col2.metric("Nivel", "Fokin avanzado")

st.divider()

# ─── EDITAR DATOS ─────────────────────────────────────────────────
with st.expander("Editar datos personales", expanded=False):
    nuevo_nombre = st.text_input("Nombre", value=nombre_actual)
    nueva_edad   = st.number_input("Edad", min_value=10, max_value=100, value=int(edad_actual))

    if st.button("Guardar datos", use_container_width=True):
        c.execute(
            "UPDATE perfil SET nombre = ?, edad = ? WHERE id = 1",
            (nuevo_nombre, nueva_edad)
        )
        conn.commit()
        st.toast("Perfil actualizado")
        st.rerun()

# ══════════════════════════════════════════════════════════════════
# SECCIÓN 2: Registrar peso hoy
# ══════════════════════════════════════════════════════════════════
st.subheader("Registrar Peso Hoy")

col_peso, col_btn = st.columns([2, 1])
nuevo_peso = col_peso.number_input(
    "Peso corporal (lb)",
    min_value=50.0, max_value=500.0,
    value=float(ultimo_peso_row[0]) if ultimo_peso_row else 150.0,
    step=0.5,
    label_visibility="collapsed"
)

if col_btn.button("Registrar", use_container_width=True, type="primary"):
    c.execute("INSERT INTO peso_corporal (peso) VALUES (?)", (nuevo_peso,))
    conn.commit()
    st.toast(f"✅ {nuevo_peso:.1f} lb registradas")
    st.rerun()

# ══════════════════════════════════════════════════════════════════
# SECCIÓN 3: Historial de peso
# ══════════════════════════════════════════════════════════════════
st.subheader("📈 Evolución de Peso Corporal")

df_peso = pd.read_sql_query(
    "SELECT peso, fecha FROM peso_corporal ORDER BY fecha ASC",
    conn
)

if df_peso.empty:
    st.info("Aún no hay registros de peso. ¡Empieza registrando tu peso hoy!")
else:
    df_peso['fecha'] = pd.to_datetime(df_peso['fecha'])
    df_peso['fecha_str'] = df_peso['fecha'].dt.strftime('%d/%m/%Y')

    # ── Gráfica de evolución ──
    import altair as alt

    chart = alt.Chart(df_peso).mark_line(
        point=alt.OverlayMarkDef(size=60, filled=True),
        color="#FF4B4B",
        strokeWidth=2
    ).encode(
        x=alt.X('fecha:T', title='Fecha', axis=alt.Axis(format='%d/%m')),
        y=alt.Y('peso:Q', title='Peso (lb)', scale=alt.Scale(zero=False)),
        tooltip=[
            alt.Tooltip('fecha_str:N', title='Fecha'),
            alt.Tooltip('peso:Q', title='Peso (lb)', format='.1f')
        ]
    ).properties(height=300)

    st.altair_chart(chart, use_container_width=True)

    # ── Tabla con delta ──
    st.subheader("📋 Registros")
    df_tabla = df_peso[['fecha_str', 'peso']].copy()
    df_tabla = df_tabla.rename(columns={'fecha_str': 'Fecha', 'peso': 'Peso (lb)'})
    df_tabla['Cambio'] = df_tabla['Peso (lb)'].diff().round(1)

    def formato_cambio(val):
        if pd.isna(val):
            return "—"
        if val > 0:
            return f"⬆️ +{val:.1f}"
        elif val < 0:
            return f"⬇️ {val:.1f}"
        else:
            return "➡️ 0.0"

    df_tabla['Cambio'] = df_tabla['Cambio'].apply(formato_cambio)
    df_tabla = df_tabla.iloc[::-1].reset_index(drop=True)  # más reciente primero

    st.dataframe(df_tabla, use_container_width=True, hide_index=True)

    # ── Resumen rápido ──
    if len(df_peso) >= 2:
        st.divider()
        peso_inicial = df_peso['peso'].iloc[0]
        peso_actual  = df_peso['peso'].iloc[-1]
        diferencia   = peso_actual - peso_inicial
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Peso inicial", f"{peso_inicial:.1f} lb")
        col_b.metric("Peso actual",  f"{peso_actual:.1f} lb")
        col_c.metric("Cambio total", f"{diferencia:+.1f} lb",
                     delta_color="inverse" if diferencia > 0 else "normal")

# ══════════════════════════════════════════════════════════════════
# SECCIÓN 4: Exportar historial
# ══════════════════════════════════════════════════════════════════
st.divider()
st.subheader("Exportar")

df_historial = pd.read_sql_query(
    "SELECT ejercicio, peso, reps, fecha FROM entreno ORDER BY fecha DESC",
    conn
)

if not df_historial.empty:
    csv = df_historial.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="⬇️ Descargar historial de entrenos (CSV)",
        data=csv,
        file_name=f"historial_gym_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True
    )
else:
    st.info("Aún no hay historial de entrenos para exportar.")