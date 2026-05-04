import streamlit as st
import sqlite3
import pandas as pd
import time
import api_utils
import streamlit.components.v1 as components

# Agregar un cronometro editable en cada ejercicio para registrar tiempos de descanso o duración de la serie.



# --- 1. CONFIGURACIÓN Y PERSISTENCIA ---
conn = sqlite3.connect("gym_data.db", check_same_thread=False)
c = conn.cursor()
biblioteca = api_utils.cargar_biblioteca_visual()
nombres_ejercicios = list(biblioteca.keys())

# --- 2. ESTADO DE LA SESIÓN (Cronómetro) ---
if "timer_start" not in st.session_state:
    st.session_state.timer_start = None
if "ejecutando" not in st.session_state:
    st.session_state.ejecutando = False

def format_time(seconds):
    mins, secs = divmod(int(seconds), 60)
    return f"{mins:02d}:{secs:02d}"

def reproducir_alarma():
    # URL del sonido seleccionado
    url_audio = "https://www.myinstants.com/media/sounds/discord-notification.mp3"
    
    js_code = f"""
    <script>
    // Buscamos si ya existe la instancia en la ventana actual
    if (window.gymAudio) {{
        window.gymAudio.pause();      // Detenemos cualquier sonido previo
        window.gymAudio.currentTime = 0; // REBOBINAR: Esto permite que suene de nuevo
    }} else {{
        window.gymAudio = new Audio('{url_audio}');
    }}
    
    // Intentamos reproducir
    window.gymAudio.play().catch(function(error) {{
        console.log("Error en reproducción: ", error);
    }});
    </script>
    """
    st.components.v1.html(js_code, height=0)

st.title("Entrenamiento en Curso")

# --- 3. SELECTOR Y CONTROL DE TIEMPO ---
df_rutinas_nombres = pd.read_sql_query("SELECT DISTINCT nombre_rutina FROM rutinas", conn)

if not df_rutinas_nombres.empty:
    rutina_nombre = st.selectbox("Selecciona tu rutina", df_rutinas_nombres['nombre_rutina'])
    
    col_play, col_stop = st.columns(2)
    if col_play.button("▶Iniciar Reloj", use_container_width=True):
        st.session_state.timer_start = time.time()
        st.session_state.ejecutando = True

    if col_stop.button("Terminar Rutina", use_container_width=True):
        st.session_state.timer_start = None
        st.session_state.ejecutando = False

    if st.session_state.ejecutando:
        elapsed = time.time() - st.session_state.timer_start
        st.metric("Tiempo transcurrido", format_time(elapsed))
        if st.button("🔄 Actualizar Tiempo"): st.rerun()

    st.divider()

    # --- 4. LISTA DE EJERCICIOS CON REGISTRO DETALLADO ---
    st.subheader(f"Ejercicios de: {rutina_nombre}")
    
    # Traemos los ejercicios planificados
    ejercicios_plan = pd.read_sql_query(
        "SELECT id, ejercicio, series_planificadas FROM rutinas WHERE nombre_rutina = ?", 
        conn, params=(rutina_nombre,)
    )

    for index, row in ejercicios_plan.iterrows():
        with st.expander(f"{row['ejercicio']} ({row['series_planificadas']} Series)", expanded=True):
            
            col_img, col_edit = st.columns([1, 2])
            
            with col_img:
                url = biblioteca.get(row['ejercicio'])
                if url: st.image(url, use_container_width=True)
            
            with col_edit:
                # --- FILA DE GESTIÓN: ELIMINAR Y CONFIGURAR DESCANSO ---
                c1, c2, c3 = st.columns([1, 2, 2])
                
                with c1:
                    # Creamos una llave única para el estado de confirmación de este ejercicio específico
                    confirm_key = f"confirm_del_{row['id']}"
                    if confirm_key not in st.session_state:
                        st.session_state[confirm_key] = False

                    # Si no se ha presionado la basura, mostrar el icono normal
                    if not st.session_state[confirm_key]:
                        if st.button(" Eliminar Ejercicio ", key=f"btn_del_{row['id']}", help="Eliminar ejercicio"):
                            st.session_state[confirm_key] = True
                            st.rerun()
                    else:
                        # Si ya se presionó, mostrar botones de Confirmar / Cancelar
                        col_conf, col_can = st.columns(2)
                        if col_conf.button("Borrar      ", key=f"conf_{row['id']}", help="Confirmar eliminación"):
                            c.execute("DELETE FROM rutinas WHERE id = ?", (row['id'],))
                            conn.commit()
                            # Limpiamos el estado antes de recargar
                            del st.session_state[confirm_key]
                            st.rerun()
                            
                        if col_can.button("Cancelar     ", key=f"can_{row['id']}", help="Cancelar"):
                            st.session_state[confirm_key] = False
                            st.rerun()
                
                with c2:
                    # Input de minutos (activará el pad numérico en tu iPhone 13)
                    mins = st.number_input("Min", 0, 10, 2, key=f"m_{row['id']}")
                
                with c3:
                    # Input de segundos
                    segs = st.number_input("Seg", 0, 59, 20, key=f"s_{row['id']}")

                # Botón de acción: Al estar fuera de un popover, solo se dispara al hacer clic
                if st.button("⏱️ Iniciar Descanso", key=f"start_{row['id']}", use_container_width=True):
                    total = (mins * 60) + segs
                    progreso = st.progress(0)
                    status = st.empty()
                    
                    # Bucle del temporizador
                    for t in range(total, -1, -1):
                        m, s = divmod(t, 60)
                        status.metric("Descansando...", f"{m:02d}:{s:02d}")
                        progreso.progress(1.0 - (t / total) if total > 0 else 1.0)
                        time.sleep(1)
                    
                    # EL SONIDO SOLO SE ACTIVA AQUÍ (Al finalizar el bucle)
                    reproducir_alarma() 
                    status.success("¡TIEMPO AGOTADO!")

            # --- TABLA DE REGISTRO (Pad numérico para iPhone) ---
            filas = []
            for i in range(row['series_planificadas']):
                filas.append({"Serie": i + 1, "Peso (kg)": 0.0, "Reps": 0, "✅": False})
            
            df_temp = pd.DataFrame(filas)
            
            # Editor de datos optimizado para móvil
            tabla_editada = st.data_editor(
                df_temp,
                key=f"ed_{row['id']}",
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Peso (kg)": st.column_config.NumberColumn("Peso", format="%.1f", step=0.5),
                    "Reps": st.column_config.NumberColumn("Reps", step=1),
                    "✅": st.column_config.CheckboxColumn("Hecho")
                }
            )

            # Botón para subir a la base de datos de historial
            if st.button(f"Guardar {row['ejercicio']}", key=f"save_{row['id']}", use_container_width=True):
                completados = tabla_editada[tabla_editada['✅'] == True]
                if not completados.empty:
                    for _, s in completados.iterrows():
                        c.execute("INSERT INTO entreno (ejercicio, peso, reps) VALUES (?, ?, ?)",
                                  (row['ejercicio'], s['Peso (kg)'], s['Reps']))
                    conn.commit()
                    st.toast(f"¡{len(completados)} series de {row['ejercicio']} guardadas!")
                else:
                    st.warning("Marca el check ✅ antes de guardar")

    # --- 5. AGREGAR EJERCICIO EXTRA (On-the-fly) ---
    st.divider()
    with st.expander("➕ Añadir ejercicio extra hoy"):
        nuevo_ej = st.selectbox("Buscar en la biblioteca", nombres_ejercicios)
        if nuevo_ej:
            prev = biblioteca.get(nuevo_ej)
            if prev: st.image(prev, width=150)
            
        n_ser = st.number_input("Series", min_value=1, value=3)
        if st.button("Agregar a la sesión"):
            c.execute("INSERT INTO rutinas (nombre_rutina, ejercicio, series_planificadas) VALUES (?, ?, ?)",
                      (rutina_nombre, nuevo_ej, n_ser))
            conn.commit()
            st.rerun()

else:
    st.info("Crea una rutina en la sección de 'Entrenamientos' para empezar.")