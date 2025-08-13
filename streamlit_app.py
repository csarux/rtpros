# streamlit_app.py - Punto de entrada directo para Streamlit Cloud
# Este archivo DEBE estar en la raíz del repositorio para que Streamlit Cloud lo detecte

import sys
import os
from pathlib import Path

# Configurar el entorno ANTES de cualquier importación de Streamlit
def setup_environment():
    """Configura el entorno para que funcione tanto en Cloud como localmente"""
    current_dir = Path(__file__).parent.absolute()
    
    # Verificar si existe src en el directorio actual
    src_path = current_dir / "src"
    if src_path.exists():
        sys.path.insert(0, str(src_path))
        sys.path.insert(0, str(src_path / "streamlit"))
        
        # NO cambiar directorio de trabajo - solo agregar al path
        streamlit_dir = src_path / "streamlit"
        return streamlit_dir.exists()
    
    return False

# Configurar entorno
env_setup = setup_environment()
project_root = Path(__file__).parent.absolute()

if not env_setup:
    # Mostrar información de debug
    import streamlit as st
    st.error("❌ Error: No se puede encontrar la estructura del proyecto")
    st.error(f"Directorio del script: {project_root}")
    st.error(f"Existe src/?: {(project_root / 'src').exists()}")
    if (project_root / 'src').exists():
        st.error(f"Contenido de src/: {list((project_root / 'src').iterdir())}")
        st.error(f"Existe src/streamlit/?: {(project_root / 'src' / 'streamlit').exists()}")
        if (project_root / 'src' / 'streamlit').exists():
            st.error(f"Contenido de src/streamlit/: {list((project_root / 'src' / 'streamlit').iterdir())}")
    st.stop()

# Ahora ejecutar la aplicación principal directamente
try:
    # Usar siempre la ruta absoluta
    app_file = project_root / "src" / "streamlit" / "app.py"
    
    if app_file.exists():
        with open(app_file, "r", encoding="utf-8") as f:
            exec(f.read())
    else:
        import streamlit as st
        st.error("❌ No se puede encontrar app.py")
        st.error(f"Buscando en: {app_file}")
        st.error(f"Directorio actual: {Path.cwd()}")
except Exception as e:
    import streamlit as st
    st.error(f"❌ Error ejecutando la aplicación: {e}")
    st.error(f"Directorio de trabajo: {os.getcwd()}")
    st.error(f"Python path: {sys.path[:5]}")  # Solo primeros 5 para no saturar
