import streamlit as st
import pandas as pd

def mostrar(dfs, save_data):
    st.markdown("<h2 style='color: #FFD700;'>➕ Registro de Nuevo Colaborador</h2>", unsafe_allow_html=True)
    
   # --- BLOQUE NUEVO: CARGA DE PARÁMETROS DINÁMICOS ---
    df_para = dfs.get("PARAMETROS", pd.DataFrame())
    
    # --- CÓDIGO CHISMOSO PARA DEBUG (BORRAREMOS ESTO DESPUÉS) ---
    st.info(f"Hojas que el sistema está leyendo: {list(dfs.keys())}")
    if df_para.empty:
        st.error("🚨 ALERTA: La hoja PARAMETROS está vacía o no se encontró en Google Sheets.")
    else:
        st.success(f"✅ Hoja encontrada. Columnas leídas: {df_para.columns.tolist()}")
    # -------------------------------------------------------------
    
    # TRUCO ANTIFALLOS: Quitamos espacios ocultos al inicio o final de los títulos en Excel
    if not df_para.empty:
        df_para.columns = df_para.columns.str.strip()
    
    # Extraemos las listas limpias (quitando vacíos)
    def obtener_lista(columna, default):
        if columna in df_para.columns:
            # Dropna quita vacíos, astype(str) asegura que sea texto, y strip() quita espacios
            lista = df_para[columna].dropna().astype(str).str.strip().unique().tolist()
            # Filtramos por si hay celdas que solo tenían espacios en blanco
            lista = [item for item in lista if item and item.lower() != "nan"]
            return lista if lista else default
        return default

    # AHORA SÍ: Usamos los nombres exactos con GUION BAJO tal cual tu Excel
    lista_sexo = obtener_lista("SEXO", ["Masculino", "Femenino"])
    lista_estado = obtener_lista("ESTADO_CIVIL", ["Soltero(a)", "Casado(a)", "Divorciado(a)", "Conviviente", "Viudo(a)"])
    lista_sede = obtener_lista("SEDE_TRABAJO", ["Sede Central"]) 
    # --------------------------------------------------

    with st.form("reg_p", clear_on_submit=True):
        st.write("### Alta de Nuevo Trabajador")
        d_dni = st.text_input("DNI").strip()
        
        # 1. Separamos Apellidos y Nombres (Asegurando Mayúsculas)
        ape_form = st.text_input("Apellidos").upper().strip()
        nom_form = st.text_input("Nombres").upper().strip()
        
        # Combinamos para "apellidos y nombres" (Apellido, Nombre)
        nom_comp = f"{ape_form}, {nom_form}" if ape_form and nom_form else ""
        
        # 2. Listas desplegables CONECTADAS AL EXCEL
        sexo_form = st.selectbox("Sexo", lista_sexo)
        estado_form = st.selectbox("Estado Civil", lista_estado)
        sede_form = st.selectbox("Sede de Trabajo", lista_sede)
        
        link_form = st.text_input("Link File").strip()

        if st.form_submit_button("Registrar"):
            if d_dni and ape_form and nom_form:
                # Cálculo del ID para PERSONAL
                next_id_personal = dfs["PERSONAL"]["id"].max() + 1 if not dfs["PERSONAL"].empty else 1
                
                # A. Guardamos en PERSONAL
                nuevo_personal = {
                    "id": next_id_personal, 
                    "dni": d_dni, 
                    "apellidos": ape_form, 
                    "nombres": nom_form, 
                    "apellidos y nombres": nom_comp, 
                    "sexo": sexo_form, 
                    "estado_civil": estado_form, 
                    "sede": sede_form, 
                    "link": link_form
                }
                dfs["PERSONAL"] = pd.concat([dfs["PERSONAL"], pd.DataFrame([nuevo_personal])], ignore_index=True)
                
                # B. Crear automáticamente entrada en DATOS GENERALES
                nid_dg = dfs["DATOS GENERALES"]["id"].max() + 1 if not dfs["DATOS GENERALES"].empty else 1
                nuevo_dg_basico = {
                    "id": nid_dg, 
                    "dni": d_dni, 
                    "apellidos y nombres": nom_comp,
                    "sexo": sexo_form,         # Agregué estos para que ya nazca con datos
                    "estado_civil": estado_form,
                    "sede": sede_form
                }
                dfs["DATOS GENERALES"] = pd.concat([dfs["DATOS GENERALES"], pd.DataFrame([nuevo_dg_basico])], ignore_index=True)
                
                # Guardamos y reiniciamos
                save_data(dfs)
                st.success(f"✅ {nom_comp} registrado correctamente")
                st.rerun()
            else: 
                st.error("⚠️ Por favor, complete al menos el DNI, Apellidos y Nombres.")
