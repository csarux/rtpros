import streamlit as st
import pandas as pd
import sys
import os

# Añade el directorio src al path para importar aclinprot como acp
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import aclinprot as acp

st.title("Procesamiento de prescripciones de radioterapia")

# Espacio para subir el archivo CSV
uploaded_file = st.file_uploader("Sube el archivo de prescripción (CSV)", type="csv")

if uploaded_file is not None:
    # Guarda el archivo temporalmente si es necesario
    # o pásalo directamente si acp.parse_prescription acepta un buffer
    try:
        # Si parse_prescription acepta un buffer, pásalo directamente:
        pvdf, ccdf, oardf = acp.parse_prescription(uploaded_file)
        
        st.subheader("Prescripción principal")
        st.dataframe(pvdf)
        
        st.subheader("Condiciones clínicas")
        st.dataframe(ccdf)
        
        st.subheader("Restricciones OAR")
        st.dataframe(oardf)
    except Exception as e:
        st.error(f"Error procesando el archivo: {e}")
else:
    st.info("Por favor, sube un archivo CSV para comenzar.")