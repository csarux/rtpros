import streamlit as st
import pandas as pd
import sys
import os
from io import StringIO
import traceback

# Añade el directorio src al path para importar aclinprot como acp
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../aclinprot')))
import aclinprot as acp

st.title("Creación de protocolos clínicos mediante prescripciones de radioterapia")

# --- Barra lateral ---
st.sidebar.header("Identificadores del protocolo clínico")
protocolo_id = st.sidebar.text_input("Identificación del protocolo", value="ProtocoloID")
plan_id = st.sidebar.text_input("Identificación del Plan", value="PlanID")
prot_out = st.sidebar.text_input("Archivo Protocolo Clínico", value="ClinicalProtocol.xml")
treatment_site = st.sidebar.selectbox(
    "Sitio de tratamiento",
    options=["Lungs", "Head and Neck", "Brain", "Thorax", "Abdomen"],
    index=2,
    key="treatment_site",
)
treatment_site = st.sidebar.text_input("Editar sitio de tratamiento", value=treatment_site)

uploaded_file = st.file_uploader("Sube el archivo de prescripción (CSV)", type="csv")

# Estado para edición
if 'edit_csv' not in st.session_state:
    st.session_state.edit_csv = False
if 'csv_content' not in st.session_state:
    st.session_state.csv_content = None

# Botón para editar el archivo CSV
if uploaded_file is not None:
    if st.sidebar.button("Editar archivo CSV"):
        st.session_state.edit_csv = True
        st.session_state.csv_content = uploaded_file.getvalue().decode("utf-8")

# Editor de texto para el CSV
if uploaded_file is not None and st.session_state.edit_csv:
    edited_csv = st.text_area("Edita el archivo CSV", value=st.session_state.csv_content, height=400)
    if st.button("Guardar cambios y recargar"):
        st.session_state.csv_content = edited_csv
        st.session_state.edit_csv = False
        st.rerun()  # <-- Fuerza recarga para mostrar el contenido actualizado

# Mostrar DataFrames (si no estamos editando)
if uploaded_file is not None and not st.session_state.edit_csv:
    csv_string = st.session_state.csv_content if st.session_state.csv_content else None
    if csv_string:
        file_to_parse = StringIO(csv_string)
    else:
        uploaded_file.seek(0)
        file_to_parse = uploaded_file

    try:
        pvdf, ccdf, oardf = acp.parse_prescription(file_to_parse)
        st.subheader("Prescripción principal")
        st.dataframe(pvdf, use_container_width=True)
        st.subheader("Condiciones clínicas")
        st.dataframe(ccdf, use_container_width=True)
        st.subheader("Restricciones OAR")
        st.dataframe(oardf, use_container_width=True)
    except Exception as e:
        st.error(f"Error procesando el archivo: {e}")

# Generar protocolo clínico y permitir descarga
if st.sidebar.button("Generar protocolo clínico"):
    ruta_protocolo = os.path.abspath(os.getcwd())
    os.makedirs(ruta_protocolo, exist_ok=True)

    csv_string = st.session_state.csv_content if st.session_state.csv_content else None
    prescription_file = StringIO(csv_string) if csv_string else uploaded_file
    if not csv_string:
        uploaded_file.seek(0)

    try:
        acp.convertPrescriptionIntoClinicalProtocol(
            prescription=StringIO(csv_string) if csv_string else uploaded_file,
            ProtocolID=protocolo_id,
            TreatmentSite=treatment_site,
            PlanID=plan_id,
            ProtOut=prot_out
        )
        st.success(f"Protocolo clínico generado en {prot_out}")

        # Ruta completa al archivo generado
        xml_path = os.path.join(ruta_protocolo, prot_out)
        # Lee el archivo XML como texto
        with open(xml_path, "r", encoding="utf-8") as f:
            xml_content = f.read()
        # Botón de descarga
        st.download_button(
            label="Descargar protocolo clínico XML",
            data=xml_content,
            file_name=prot_out,
            mime="application/xml"
        )
    except Exception as e:
        st.error(f"Error generando el protocolo clínico: {e}")

# Mostrar mensaje solo si no hay archivo subido
if uploaded_file is None:
    st.info("Por favor, sube la prescripción exportada en formato CSV para comenzar.")