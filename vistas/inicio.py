import streamlit as st

st.title("¡Hola, Christopher!")
st.write("Bienvenido a tu panel de control.")

st.info("Selecciona 'Entrenamientos' en el menú lateral para registrar tu sesión de hoy.")

# Podrías agregar una frase motivacional o resumen rápido
st.metric(label="Estado Actual", value="Activo", delta="Fuerza")