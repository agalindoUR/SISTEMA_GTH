import streamlit as st
import pandas as pd

def mostrar(dfs, save_data):
    st.markdown("<h2 style='color: #FFD700;'>➕ Registro de Nuevo Colaborador</h2>", unsafe_allow_html=True)
    
    with st.form("reg_p", clear_on_submit=True):
        st.write("### Alta de Nuevo Trabajador")
        d_dni = st.text_input("DNI").strip()
        # 1. Separamos Apellidos y Nombres (Asegurando Mayúsculas)
        ape_form = st.text_input("Apellidos").upper().strip()
        nom_form = st.text_input("Nombres").upper().strip()
        # Combinamos para "apellidos y nombres" (Apellido, Nombre)
        nom_comp = f"{ape_form}, {nom_form}" if ape_form and nom_form else ""
        # 2. Listas desglosables
        sexo_form = st.selectbox("Sexo", ["Masculino", "Femenino"])
        estado_form = st.selectbox("Estado Civil", ["Soltero(a)", "Casado(a)", "Divorciado(a)", "Conviviente", "Viudo(a)", "Otro"])
        sede_form = st.selectbox("Sede de Trabajo", ["Local Giraldez", "Local San Carlos", "Local Abancay", "Local Lince", "Local Pueblo Libre"])
        link_form = st.text_input("Link File").strip()

        if st.form_submit_button("Registrar"):
            if d_dni and ape_form and nom_form:
                # Cálculo robusto del ID para PERSONAL (ID único por persona)
                next_id_personal = dfs["PERSONAL"]["id"].max() + 1 if not dfs["PERSONAL"].empty else 1
                # A. Guardamos en PERSONAL (Lista Maestra)
                nuevo_personal = {"id": next_id_personal, "dni": d_dni, "apellidos": ape_form, "nombres": nom_form, "apellidos y nombres": nom_comp, "sexo": sexo_form, "estado_civil": estado_form, "sede": sede_form, "link": link_form}
                dfs["PERSONAL"] = pd.concat([dfs["PERSONAL"], pd.DataFrame([nuevo_personal])], ignore_index=True)
                
                # CORRECCIÓN VINCULACIÓN: Crear automáticamente entrada básica en DATOS GENERALES
                nid_dg = dfs["DATOS GENERALES"]["id"].max() + 1 if not dfs["DATOS GENERALES"].empty else 1
                nuevo_dg_basico = {"id": nid_dg, "dni": d_dni, "apellidos y nombres": nom_comp}
                dfs["DATOS GENERALES"] = pd.concat([dfs["DATOS GENERALES"], pd.DataFrame([nuevo_dg_basico])], ignore_index=True)
                
                # Guardamos ambos cambios
                save_data(dfs)
                st.success("Trabajador registrado correctamente")
                st.rerun()
            else: 
                st.error("⚠️ Por favor, complete al menos el DNI, Apellidos y Nombres.")
