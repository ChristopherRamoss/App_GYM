import streamlit as st
import api_utils
import sqlite3
import pandas as pd
import json
import os

# ---------------------------------------------------------
# 1. CONFIGURACIÓN DE LA BASE DE DATOS (Persistencia)
# ---------------------------------------------------------
conn = sqlite3.connect("gym_data.db", check_same_thread=False)
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS entreno (ejercicio TEXT, peso REAL, reps INTEGER)")
conn.commit()

# ---------------------------------------------------------
# 2. CARGA DE ACTIVOS Y DATOS (Lógica de Negocio)
# ---------------------------------------------------------
# Cargamos la biblioteca visual (nombres traducidos e imágenes)
biblioteca = api_utils.cargar_biblioteca_visual()
nombres = list(biblioteca.keys())

# ---------------------------------------------------------
# 3. CABECERA E INTERFAZ PRINCIPAL (UI)
# ---------------------------------------------------------
st.title("Hola Christopher. A entrenar")

# Selector reactivo: Cambia la imagen instantáneamente al seleccionar
ejercicio_sel = st.selectbox("Selecciona Ejercicio", nombres)

# ---------------------------------------------------------
# 4. PANEL DE VISTA PREVIA (Visualización Dinámica)
# ---------------------------------------------------------
col_info, col_img = st.columns([2, 1])

with col_info:
    st.write(f"### {ejercicio_sel}")
    # Aquí podrías agregar el músculo principal si lo extraes del JSON

with col_img:
    url_img = biblioteca.get(ejercicio_sel)
    if url_img:
        st.image(url_img, use_container_width=True)
    else:
        st.warning("📷 Sin imagen")

# ---------------------------------------------------------
# 5. ENTRADA DE DATOS (Controlador de Registro)
# ---------------------------------------------------------
with st.form("registro_serie", clear_on_submit=True):
    peso = st.number_input("Peso (kg)", min_value=0.0, step=0.5)
    reps = st.number_input("Repeticiones", min_value=0, step=1)
    
    if st.form_submit_button("Guardar Serie"):
        try:
            # Operación de inserción en SQLite
            c.execute("INSERT INTO entreno (ejercicio, peso, reps) VALUES (?, ?, ?)", 
                      (ejercicio_sel, peso, reps))
            conn.commit()
            
            st.success(f"¡Guardado! {ejercicio_sel}: {peso}kg x {reps} reps")
            
            # Recargamos la app para que los cambios se vean en la tabla inferior
            st.rerun() 
        except Exception as e:
            st.error(f"Error al guardar en la base de datos: {e}")


# ---------------------------------------------------------
# 6. HISTORIAL Y REPORTES (Visualización de Datos)
# ---------------------------------------------------------
st.divider() # Línea visual divisoria
st.subheader("Últimas series registradas")

# Leemos directamente de la DB para asegurar datos frescos
df = pd.read_sql_query("SELECT * FROM entreno", conn)

# Mostramos las últimas 10 entradas de forma estética
if not df.empty:
    st.dataframe(df.tail(10), use_container_width=True)
else:
    st.info("Aún no hay series registradas hoy.")