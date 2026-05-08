import streamlit as st

PAGES = {
    "inicio":      ("vistas/inicio.py",         "🏠",  "Inicio"),
    "entrenar":    ("vistas/mis_rutinas.py",     "▶️",  "Entrenar"),
    "rutinas":     ("vistas/entrenamientos.py",  "📋",  "Rutinas"),
    "stats":       ("vistas/estadisticas.py",    "📊",  "Stats"),
    "perfil":      ("vistas/perfil.py",          "👤",  "Perfil"),
}

def inject_bottom_nav(active: str = "inicio"):
    # 1. Ocultar TODO lo de Streamlit que no queremos
    st.markdown("""
    <style>
    section[data-testid="stSidebar"]            { display:none !important; }
    div[data-testid="stSidebarCollapsedControl"] { display:none !important; }
    button[data-testid="stSidebarNavToggle"]     { display:none !important; }
    header[data-testid="stHeader"]               { display:none !important; }
    div[data-testid="stToolbar"]                 { display:none !important; }
    div[data-testid="stDecoration"]              { display:none !important; }
    footer                                       { display:none !important; }
    .stApp { background:#0f0f0f !important; }
    /* Padding para que el contenido no quede tapado por la barra */
    .block-container,
    div[data-testid="stMainBlockContainer"] {
        padding-bottom: 90px !important;
        padding-top: 12px !important;
        max-width: 480px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # 2. Construir los items del nav
    items_html = ""

    for key, (path, icon, label) in PAGES.items():

        is_active = key == active

        color = "#e63946" if is_active else "#666"
        weight = "700" if is_active else "500"

        indicator = (
            '<div style="width:4px;height:4px;border-radius:50%;background:#e63946;margin-top:2px;"></div>'
            if is_active else
            '<div style="height:6px;"></div>'
        )

        items_html += f'''
        <a href="?nav={key}" style="
            flex:1;
            display:flex;
            flex-direction:column;
            align-items:center;
            justify-content:center;
            gap:2px;
            text-decoration:none;
            color:{color};
            font-size:10px;
            font-weight:{weight};
            padding:8px 4px 0px;
            -webkit-tap-highlight-color:transparent;
        ">
            <span style="font-size:20px;">{icon}</span>
            <span>{label}</span>
            {indicator}
        </a>
        '''
        # 3. Inyectar la barra como HTML fijo
        st.markdown(f"""
        <!-- BOTTOM NAV -->
        <div id="bottom-nav" style="
            position:fixed; bottom:0; left:0; right:0; z-index:9999;
            background:rgba(14,14,14,0.97);
            backdrop-filter:blur(20px); -webkit-backdrop-filter:blur(20px);
            border-top:1px solid #222;
            display:flex; flex-direction:row;
            padding: 0 8px calc(env(safe-area-inset-bottom) + 8px) 32px;
            box-shadow:0 -4px 24px rgba(0,0,0,0.6);">
            {items_html}
        </div>
        """, unsafe_allow_html=True)



        # 5. Leer el param de navegación y hacer switch_page
        nav_param = st.query_params.get("nav", None)
        if nav_param and nav_param != active and nav_param in PAGES:
            target_path = PAGES[nav_param][0]
            st.switch_page(target_path)