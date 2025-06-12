import streamlit as st
import pandas as pd
import sys
import os
from io import StringIO
import traceback
import difflib


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
    options=["Abdomen",
             "Bone",
             "Brain", 
             "Breasts", 
             "Breast, Left", 
             "Breast, Right", 
             "Head and Neck", 
             "Liver",
             "Lumbar spine",
             "Lungs", 
             "Lung, Left", 
             "Lung, Right", 
             "Pelvis",
             "Prostate",
             "Rectum",
             "Stomach",
             "Thorax", ],
    index=0,
    key="treatment_site",
)
treatment_site = st.sidebar.text_input("Editar sitio de tratamiento", value=treatment_site)


tab1, tab2, tab3 = st.tabs(["Prescripción", "Corrección de estructuras", "Verificación restricciones OAR"])

with tab1:
    # Aquí va tu lógica actual de prescripción (ya la tienes implementada)
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
            pvdfs, ccdfs, oardfs = acp.parse_prescription(file_to_parse)
            num_prescripciones = len(pvdfs)

            if num_prescripciones > 1:
                if 'prescripcion_idx' not in st.session_state:
                    st.session_state.prescripcion_idx = 0
                prescripcion_idx = st.sidebar.selectbox(
                    "Selecciona la prescripción",
                    options=list(range(num_prescripciones)),
                    format_func=lambda x: f"Prescripción {x+1}",
                    index=st.session_state.prescripcion_idx,
                    key="prescripcion_idx"
                )
            else:
                prescripcion_idx = 0

            pvdf = st.session_state.get('pvdf', pvdfs[prescripcion_idx])
            ccdf = st.session_state.get('ccdf', ccdfs[prescripcion_idx])
            oardf = st.session_state.get('oardf', oardfs[prescripcion_idx])
            
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

        # Usa los dataframes corregidos si existen en session_state
        pvdf_to_use = st.session_state.get('pvdf', pvdf)
        ccdf_to_use = st.session_state.get('ccdf', ccdf)
        oardf_to_use = st.session_state.get('oardf', oardf)

        try:
            acp.convertPrescriptionIntoClinicalProtocol(
                prescription_or_pvdf=pvdf_to_use,
                ccdf=ccdf_to_use,
                oardf=oardf_to_use,
                ProtocolID=protocolo_id,
                TreatmentSite=treatment_site,
                PlanID=plan_id,
                ProtOut=prot_out,
                PrescriptionIndex=prescripcion_idx,
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
            st.code(traceback.format_exc(), language="python")

    # Mostrar mensaje solo si no hay archivo subido
    if uploaded_file is None:
        st.info("Por favor, sube la prescripción exportada en formato CSV para comenzar.")

    pass

with tab2:
    st.header("Corrección de estructuras")
    dicom_file = st.file_uploader("Sube el archivo DICOM RT Structure Set", type=["dcm"], key="dicom_uploader")
    if dicom_file is not None:
        cont_names = acp.readContouringStructureNames(dicom_file)
        contStrdf = pd.DataFrame(cont_names, columns=['Contouring'])
        st.write("Estructuras en el RT Structure Set:")
        st.dataframe(contStrdf)

        # Unir todos los nombres únicos de estructuras de la prescripción
        pres_names = set(pvdf['Volume'].dropna().tolist()) | set(ccdf['Volume'].dropna().tolist()) | set(oardf['Organ'].dropna().tolist())
        pres_names = list(pres_names)
        st.write("Estructuras en la prescripción:")
        st.dataframe(pd.DataFrame(pres_names, columns=['Prescripción']))

        # Sugerencia automática
        suggestions = {}
        for pres_name in pres_names:
            match = difflib.get_close_matches(pres_name, cont_names, n=1)
            suggestions[pres_name] = match[0] if match else cont_names[0]

        # Selección manual
        mapping = {}
        st.write("Relaciona cada estructura de la prescripción con una del contorneo:")
        for pres_name in pres_names:
            default = suggestions[pres_name]
            selected = st.selectbox(
                f"Prescripción: {pres_name}",
                options=cont_names,
                index=cont_names.index(default),
                key=f"map_{pres_name}"
            )
            mapping[pres_name] = selected

        # Mostrar el mapeo final
        mapping_df = pd.DataFrame(list(mapping.items()), columns=["Prescripción", "Contorneo"])
        st.write("Correspondencia final:")
        st.dataframe(mapping_df)

        # Botón para aplicar la corrección
        if st.button("Aplicar corrección de nombres"):
            strNameChanges = pd.DataFrame(
                [{'Old': old, 'New': new} for old, new in mapping.items()]
            )
            pvdf['Volume'] = pvdf['Volume'].replace(mapping)
            ccdf['Volume'] = ccdf['Volume'].replace(mapping)
            oardf['Organ'] = oardf['Organ'].replace(mapping)

            # Guarda los dataframes corregidos en session_state
            st.session_state.pvdf = pvdf
            st.session_state.ccdf = ccdf
            st.session_state.oardf = oardf

            st.success("Nombres de estructuras actualizados en los tres dataframes!")
            st.rerun()

    pass

with tab3:
    rerun_needed = False
    st.header("Verificación de DosimPars en OARs")
    # Usa el oardf corregido si existe
    oardf_to_check = st.session_state.get('oardf', oardf if 'oardf' in locals() else None)
    if oardf_to_check is not None:
        df_check = acp.checkDosimPars(oardf_to_check)
        st.write("Resultado de la verificación de DosimPars:")
        st.dataframe(df_check, use_container_width=True)

        # Selección de fila para editar/borrar
        if not df_check.empty:
            idx_selected = st.selectbox(
                "Selecciona una restricción para editar o borrar:",
                options=df_check.index,
                format_func=lambda i: f"{df_check.loc[i, 'Organ']} | {df_check.loc[i, 'DosimPar']} | Reconocida: {df_check.loc[i, 'Recognized']}"
            )
            selected_row = df_check.loc[idx_selected]

            # Añadir restricción
            if 'show_form_add_constraint' not in st.session_state:
                st.session_state.show_form_add_constraint = False

            if st.button("Corregir restricción"):
                st.session_state.show_form_add_constraint = True

            if st.session_state.show_form_add_constraint:
                st.write("Añadir o corregir una restricción DosimPar para el órgano seleccionado:")
                with st.form("form_add_constraint", clear_on_submit=True):
                    organ_selected = st.text_input("Órgano", value=selected_row['Organ'], disabled=True)
                    dosimpar_new = st.text_input("Restricción (DosimPar)", value=selected_row['DosimPar'])
                    submitted = st.form_submit_button("Aceptar")
                    if submitted:
                        # Usa la función addDosimPar de aclinprot
                        oardf = acp.addDosimPar(oardf, organ_selected, dosimpar_new)
                        st.session_state.oardf = oardf
                        st.session_state.show_form_add_constraint = False
                        rerun_needed = True

            # Borrar restricción
            if st.button("Borrar"):
                organ = selected_row['Organ']
                dosimpar = selected_row['DosimPar']
                idx_oar = oardf_to_check[oardf_to_check['Organ'] == organ].index
                if not idx_oar.empty:
                    dosimpars_list = oardf_to_check.at[idx_oar[0], 'DosimPars']
                    if dosimpar in dosimpars_list:
                        dosimpars_list.remove(dosimpar)
                        st.session_state.oardf = oardf_to_check
                        st.success("Restricción eliminada.")
                        st.rerun()
                    else:
                        st.warning("La restricción no se encontró en la lista.")
            if rerun_needed:
                st.rerun()
    else:
        st.info("Primero debes cargar una prescripción para ver los DosimPars.")        
    pass

hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)