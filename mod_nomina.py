import streamlit as st
import pandas as pd

def mostrar(dfs, save_data):
    st.markdown("<h2 style='color: #FFD700;'>👥 Trabajadores registrados en el sistema</h2>", unsafe_allow_html=True)
    
    busqueda_nom = st.text_input("🔍 Buscar por apellidos, nombres o DNI (Nómina):").strip().lower()
    df_nom = dfs["PERSONAL"].copy()
    
    if busqueda_nom: 
        mask_ape = df_nom['apellidos'].fillna("").str.lower().str.contains(busqueda_nom, na=False)
        mask_nom = df_nom['nombres'].fillna("").str.lower().str.contains(busqueda_nom, na=False)
        mask_dni = df_nom['dni'].astype(str).str.contains(busqueda_nom, na=False)
        df_nom = df_nom[mask_ape | mask_nom | mask_dni]
        
    df_ver = df_nom.copy()
    
    # CORRECCIÓN NÓMINA GENERAL: Eliminar columna redundantemente
    df_ver = df_ver.drop(columns=["apellidos y nombres"], errors='ignore')
    
    df_ver.columns = [col.upper() for col in df_ver.columns]
    df_ver.insert(0, "SEL", False)
    
    ed_nom = st.data_editor(df_ver, hide_index=True, use_container_width=False, key="nomina_v3_blanco")
    filas_sel = ed_nom[ed_nom["SEL"] == True]
    
    if not filas_sel.empty:
        st.markdown("---")
        if st.button(f"🚨 ELIMINAR {len(filas_sel)} REGISTRO(S)", type="secondary", use_container_width=False):
            dnis = filas_sel["DNI"].astype(str).tolist()
            for h in dfs:
                if 'dni' in dfs[h].columns: 
                    dfs[h] = dfs[h][~dfs[h]['dni'].astype(str).isin(dnis)]
            save_data(dfs)
            st.success("Registros eliminados correctamente.")
            st.rerun()
