import streamlit as st
import api_utils
import sqlite3
import pandas as pd

# ---------------------------------------------------------
# 1. PERSISTENCIA DE DATOS (Base de Datos)
# ---------------------------------------------------------
conn = sqlite3.connect("gym_data.db", check_same_thread=False)
c = conn.cursor()

# Tabla de ejecución real (Historial)
c.execute("""CREATE TABLE IF NOT EXISTS entreno 
             (ejercicio TEXT, peso REAL, reps INTEGER, 
              fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

# Tabla de planificación (Estructura de tus rutinas)
c.execute("""CREATE TABLE IF NOT EXISTS rutinas 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, 
              nombre_rutina TEXT, 
              ejercicio TEXT, 
              series_planificadas INTEGER)""")
conn.commit()

# ---------------------------------------------------------
# 2. GESTIÓN DE ESTADO Y ACTIVOS
# ---------------------------------------------------------
# 'session_state' nos permite recordar los ejercicios que vas 
# agregando a una rutina antes de darle al botón de "Guardar"
if "ejercicios_nueva_rutina" not in st.session_state:
    st.session_state.ejercicios_nueva_rutina = []

biblioteca = api_utils.cargar_biblioteca_visual()
nombres_ejercicios = list(biblioteca.keys())

st.title("Mis Entrenamientos")

# ---------------------------------------------------------
# 3. MÓDULO DE CREACIÓN: "Configurador de Rutinas"
# ---------------------------------------------------------
@st.dialog("Diseñar Nueva Rutina")
def menu_crear_rutina():
    nombre_r = st.text_input("Nombre de la Rutina")
    
    st.write("---")
    st.subheader("Añadir Ejercicios")
    
    # Selector de ejercicio
    ej_temp = st.selectbox("Buscar Ejercicio", nombres_ejercicios)
    
    # --- NUEVA SECCIÓN: Visualización de Foto ---
    url_preview = biblioteca.get(ej_temp)
    if url_preview:
        # Mostramos una vista previa pequeña para no saturar el modal en móvil
        st.image(url_preview, caption=f"Vista previa: {ej_temp}", width=200)
    else:
        st.caption("No hay imagen disponible para este ejercicio")
    # --------------------------------------------

    series_temp = st.number_input("¿Cuántas series harás?", min_value=1, step=1)
    
    if st.button("Añadir a la lista"):
        st.session_state.ejercicios_nueva_rutina.append({
            "ejercicio": ej_temp,
            "series": series_temp
        })
        st.toast(f"{ej_temp} añadido")
    
    # Listado temporal (Se mantiene igual)
    if st.session_state.ejercicios_nueva_rutina:
        st.write("**Ejercicios en esta rutina:**")
        for item in st.session_state.ejercicios_nueva_rutina:
            st.caption(f"• {item['ejercicio']} ({item['series']} series)")
    
    if st.button("Finalizar y Guardar Todo"):
        if nombre_r and st.session_state.ejercicios_nueva_rutina:
            for item in st.session_state.ejercicios_nueva_rutina:
                c.execute("""INSERT INTO rutinas (nombre_rutina, ejercicio, series_planificadas) 
                             VALUES (?, ?, ?)""",
                          (nombre_r, item['ejercicio'], item['series']))
            conn.commit()
            st.session_state.ejercicios_nueva_rutina = [] 
            st.success(f"Rutina '{nombre_r}' lista")
            st.rerun()

# Botón de acción principal
if st.button("Crear Nueva Rutina", use_container_width=True):
    menu_crear_rutina()

st.divider()

# ---------------------------------------------------------
# 4. MÓDULO DE ENTRENAMIENTO: "Modo Ejecución"
# ---------------------------------------------------------
st.subheader("Selecciona qué vas a entrenar hoy")

df_rutinas = pd.read_sql_query("SELECT * FROM rutinas", conn)

if not df_rutinas.empty:
    rutina_activa = st.selectbox("Elige tu rutina", df_rutinas['nombre_rutina'].unique())
    
    # Filtramos los ejercicios planeados para esa rutina
    ejercicios_plan = df_rutinas[df_rutinas['nombre_rutina'] == rutina_activa]
    
    for _, fila_r in ejercicios_plan.iterrows():
        # Cada ejercicio se despliega en un 'expander' para ahorrar espacio en móvil
        with st.expander(f"🔹 {fila_r['ejercicio']} ({fila_r['series_planificadas']} Series)"):
            
            # 1. Mostrar Imagen de referencia
            url = biblioteca.get(fila_r['ejercicio'])
            if url:
                st.image(url, width=150)
            
            # 2. Crear tabla de trabajo basada en las series planificadas
            # Generamos filas vacías para que tú las llenes
            filas_trabajo = []
            for i in range(fila_r['series_planificadas']):
                filas_trabajo.append({
                    "Serie": i + 1,
                    "Peso (lb)": 0.0,
                    "Reps": 0,
                    "Hecho": False
                })
            
            df_ejecucion = pd.DataFrame(filas_trabajo)
            
            # 3. Editor de tabla (Interfaz orientada a móvil)
            tabla_editada = st.data_editor(
                df_ejecucion,
                key=f"editor_{fila_r['id']}",
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Hecho": st.column_config.CheckboxColumn("¿OK?", help="Marca para guardar esta serie")
                }
            )
            
            # 4. Botón para subir solo lo marcado como "Hecho"
            if st.button(f"Guardar progreso de {fila_r['ejercicio']}", key=f"btn_save_{fila_r['id']}"):
                series_a_guardar = tabla_editada[tabla_editada['Hecho'] == True]
                if not series_a_guardar.empty:
                    for _, s in series_a_guardar.iterrows():
                        c.execute("INSERT INTO entreno (ejercicio, peso, reps) VALUES (?, ?, ?)",
                                  (fila_r['ejercicio'], s['Peso (lb)'], s['Reps']))
                    conn.commit()
                    st.toast(f"✅ {len(series_a_guardar)} series guardadas")
                else:
                    st.warning("Marca el check de las series que terminaste")

else:
    st.info("No tienes rutinas. ¡Crea una arriba!")


# ---------------------------------------------------------
# MÓDULO DE EDICIÓN: "Gestionar Rutinas Existentes"
# ---------------------------------------------------------
@st.dialog("Editar Rutina")
def menu_editar_rutina(nombre_rutina):
    st.write(f"Editando: **{nombre_rutina}**")
    
    # 1. Consultar ejercicios actuales de esta rutina
    df_actual = pd.read_sql_query(
        "SELECT id, ejercicio, series_planificadas FROM rutinas WHERE nombre_rutina = ?", 
        conn, params=(nombre_rutina,)
    )

    # --- SECCIÓN A: Quitar Ejercicios ---
    st.subheader("Ejercicios actuales")
    for index, row in df_actual.iterrows():
        col_name, col_btn = st.columns([3, 1])
        col_name.write(f"{row['ejercicio']} ({row['series_planificadas']} series)")
        if col_btn.button("Eliminar", key=f"del_{row['id']}"):
            c.execute("DELETE FROM rutinas WHERE id = ?", (row['id'],))
            conn.commit()
            st.rerun()

    st.divider()

    # --- SECCIÓN B: Agregar Nuevo Ejercicio ---
    st.subheader("Agregar nuevo ejercicio")
    nuevo_ej = st.selectbox("Seleccionar Ejercicio", nombres_ejercicios, key="add_ej_edit")
    nuevas_series = st.number_input("Series", min_value=1, step=1, key="add_ser_edit")
    
    if st.button("Confirmar adición"):
        c.execute(
            "INSERT INTO rutinas (nombre_rutina, ejercicio, series_planificadas) VALUES (?, ?, ?)",
            (nombre_rutina, nuevo_ej, nuevas_series)
        )
        conn.commit()
        st.success(f"{nuevo_ej} agregado a {nombre_rutina}")
        st.rerun()

# ---------------------------------------------------------
# BOTÓN PARA ACTIVAR LA EDICIÓN
# ---------------------------------------------------------
# En la sección donde listas tus rutinas (Sección 4), añade este botón:
if not df_rutinas.empty:
    rutina_activa = st.selectbox("Elige tu rutina para entrenar o editar", df_rutinas['nombre_rutina'].unique())
    
    if st.button(f"Editar diseño de {rutina_activa}", use_container_width=True):
        menu_editar_rutina(rutina_activa)