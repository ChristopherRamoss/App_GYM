import streamlit as st

# Configuración básica para móvil
st.set_page_config(
    page_title="Fitness App",
    page_icon="🏋️",
    layout="wide",
    initial_sidebar_state="collapsed" # Se oculta el menú al iniciar en móvil
)

# Definición de las páginas con iconos de Material Design
inicio_page = st.Page("vistas/inicio.py", title="Inicio", icon=":material/home:")
entreno_page = st.Page("vistas/entrenamientos.py", title="Crear Rutinas", icon=":material/fitness_center:")
perfil_page = st.Page("vistas/perfil.py", title="Perfil", icon=":material/person:")
mis_rutinas_page = st.Page("vistas/mis_rutinas.py", title="Entrenar", icon=":material/play_circle:")


# Crear la navegación tipo menú lateral/sándwich
pg = st.navigation([inicio_page, entreno_page, mis_rutinas_page, perfil_page])

# Ejecutar la página seleccionada
pg.run()