import streamlit as st
import pandas as pd

def mostrar(dfs, save_data):
    st.markdown("<h2 style='color: #FFD700;'>👥 Trabajadores registrados en el sistema</h2>", unsafe_allow_html=True)
    
    busqueda_nom = st.text_input("🔍 Buscar por apellidos, nombres o DNI (Nómina):").strip().lower()
    df_nom = dfs.get("PERSONAL", pd.DataFrame()).copy()
    
    if not df_nom.empty and busqueda_nom: 
        # Convertimos todo a String de forma segura antes de buscar para evitar caídas de tipos de datos
        mask_ape = df_nom['apellidos'].fillna("").astype(str).str.lower().str.contains(busqueda_nom, na=False)
        mask_nom = df_nom['nombres'].fillna("").astype(str).str.lower().str.contains(busqueda_nom, na=False)
        mask_dni = df_nom['dni'].fillna("").astype(str).str.strip().str.contains(busqueda_nom, na=False)
        df_nom = df_nom[mask_ape | mask_nom | mask_dni]
        
    df_ver = df_nom.copy()
    
    # CORRECCIÓN NÓMINA GENERAL: Eliminar columna redundantemente
    df_ver = df_ver.drop(columns=["apellidos y nombres"], errors='ignore')
    
    # 🛠️ BLINDAJE DE COLUMNAS: Asegura que todos los nombres sean Texto puro, sin espacios y en MAYÚSCULAS
    df_ver.columns = [str(col).strip().upper() for col in df_ver.columns]
    
    # 🛠️ ANTI-DUPLICADOS: Elimina cualquier columna repetida para que st.data_editor no colapse
    df_ver = df_ver.loc[:, ~df_ver.columns.duplicated()]
    
    # Insertamos de forma segura la columna de selección
    if "SEL" in df_ver.columns:
        df_ver = df_ver.drop(columns=["SEL"])
    df_ver.insert(0, "SEL", False)
    
    # Mostramos la tabla limpia en Streamlit
    ed_nom = st.data_editor(df_ver, hide_index=True, use_container_width=False, key="nomina_v3_blanco")
    filas_sel = ed_nom[ed_nom["SEL"] == True]
    
    if not filas_sel.empty:
        st.markdown("---")
        if st.button(f"🚨 ELIMINAR {len(filas_sel)} REGISTRO(S)", type="secondary", use_container_width=False):
            # Limpiamos los DNIS seleccionados quitando espacios invisibles
            dnis = filas_sel["DNI"].astype(str).str.strip().tolist()
            
            # 🛠️ ELIMINACIÓN BLINDADA: Busca la columna 'dni' en cada pestaña sin importar si está en mayúsculas o minúsculas
            for h in dfs:
                columnas_dni = [c for c in dfs[h].columns if str(c).strip().lower() == 'dni']
                if columnas_dni: 
                    col_dni_real = columnas_dni[0] # Usa el nombre exacto que tiene en esa pestaña
                    dfs[h] = dfs[h][~dfs[h][col_dni_real].astype(str).str.strip().isin(dnis)]
                    
            save_data(dfs)
            st.success("Registros eliminados correctamente.")
            st.rerun()
