import streamlit as st

st.title("👤 Mi Perfil")

# Datos basados en tu progreso reportado
col1, col2 = st.columns(2)
col1.metric("Peso Corporal", "65.31 kg")
col2.metric("Nivel", "Intermedio")

st.write("### Ajustes")
st.button("Editar datos personales")
st.button("Exportar historial (CSV)")