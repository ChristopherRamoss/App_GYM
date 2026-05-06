import json
import os
import streamlit as st

@st.cache_data
def cargar_biblioteca_visual():
    """Devuelve {nombre: url_imagen} para compatibilidad con código existente."""
    datos = _cargar_json()
    if not datos:
        return {}

    biblioteca = {}
    base_url = "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/exercises/"

    for ej in datos:
        nombre = ej.get('name')
        lista_imagenes = ej.get('images', [])
        if nombre and lista_imagenes:
            biblioteca[nombre] = f"{base_url}{lista_imagenes[0]}"

    return biblioteca


@st.cache_data
def cargar_biblioteca_completa():
    """
    Devuelve un dict completo:
    {
      nombre: {
        "url": str,
        "primaryMuscles": [...],
        "secondaryMuscles": [...],
        "equipment": str,
        "category": str,
        "level": str,
        "instructions": [...],
        "force": str,
        "mechanic": str,
      }
    }
    """
    datos = _cargar_json()
    if not datos:
        return {}

    base_url = "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/exercises/"
    biblioteca = {}

    for ej in datos:
        nombre = ej.get('name')
        if not nombre:
            continue

        lista_imagenes = ej.get('images', [])
        url = f"{base_url}{lista_imagenes[0]}" if lista_imagenes else None

        biblioteca[nombre] = {
            "url": url,
            "primaryMuscles": ej.get('primaryMuscles', []),
            "secondaryMuscles": ej.get('secondaryMuscles', []),
            "equipment": ej.get('equipment', 'unknown'),
            "category": ej.get('category', 'unknown'),
            "level": ej.get('level', 'unknown'),
            "instructions": ej.get('instructions', []),
            "force": ej.get('force', ''),
            "mechanic": ej.get('mechanic', ''),
        }

    return biblioteca


@st.cache_data
def obtener_grupos_musculares():
    """Devuelve lista ordenada de todos los grupos musculares únicos."""
    biblioteca = cargar_biblioteca_completa()
    musculos = set()
    for info in biblioteca.values():
        for m in info.get('primaryMuscles', []):
            musculos.add(m)
    return sorted(list(musculos))


def _cargar_json():
    """Carga y parsea el JSON de ejercicios."""
    ruta = "exercises_es.json"
    if not os.path.exists(ruta):
        st.error("No se encontró exercises_es.json")
        return []
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error al procesar JSON: {e}")
        return []