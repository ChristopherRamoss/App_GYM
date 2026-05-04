import json
import os
import streamlit as st

@st.cache_data
def cargar_biblioteca_visual():
    ruta = "exercises_es.json"
    if not os.path.exists(ruta):
        return {}

    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            datos = json.load(f)
            
        biblioteca = {}
        # La URL base donde yuhonas guarda las imágenes reales
        base_url = "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/exercises/"

        for ej in datos:
            nombre = ej.get('name')
            lista_imagenes = ej.get('images', [])
            
            if nombre and lista_imagenes:
                # Tomamos la primera imagen de la lista (ej: "Ab_Roller/0.jpg")
                ruta_relativa = lista_imagenes[0]
                # Construimos la URL completa
                url_final = f"{base_url}{ruta_relativa}"
                biblioteca[nombre] = url_final
                
        return biblioteca
    except Exception as e:
        st.error(f"Error al procesar JSON: {e}")
        return {}