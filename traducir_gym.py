import json
from deep_translator import GoogleTranslator

def traducir_json():
    print("Iniciando traducción... esto puede tardar unos minutos.")
    
    with open("exercises.json", "r", encoding="utf-8") as f:
        datos = json.load(f)

    translator = GoogleTranslator(source='en', target='es')
    
    for i, ej in enumerate(datos):
        nombre_original = ej.get('name')
        try:
            # Traducimos el nombre
            nombre_es = translator.translate(nombre_original)
            ej['name'] = nombre_es
            print(f"[{i+1}/873] {nombre_original} -> {nombre_es}")
        except Exception as e:
            print(f"Error en {nombre_original}: {e}")

    # Guardamos el nuevo archivo traducido
    with open("exercises_es.json", "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    
    print("¡Listo! Archivo exercises_es.json creado.")

if __name__ == "__main__":
    traducir_json()