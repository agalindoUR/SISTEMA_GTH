# ==========================================
# MÓDULO: REPORTE GENERAL
# ==========================================

import streamlit as st
import pandas as pd
from io import BytesIO

def mostrar(dfs):
    st.markdown("<h2 style='color: #4A0000;'>📊 Reporte General de Trabajadores</h2>", unsafe_allow_html=True)
    
    df_per = dfs.get("PERSONAL", pd.DataFrame())
    df_cont = dfs.get("CONTRATOS", pd.DataFrame())
    df_gen = dfs.get("DATOS GENERALES", pd.DataFrame())
    
    if not df_per.empty and not df_cont.empty:
        # 1. Preparar datos de contratos (Fechas y Cargo)
        df_cont_sorted = df_cont.assign(f_fin_dt=pd.to_datetime(df_cont['f_fin'], errors='coerce')).sort_values('f_fin_dt')
        df_ultimos_contratos = df_cont_sorted.groupby('dni').tail(1)
        
        # 2. Armar la tabla maestra jalando la Sede de Datos Generales
        # A. Sacamos DNI y Nombres de Personal (Búsqueda inteligente a prueba de balas)
        col_nom_per = next((c for c in df_per.columns if "apellido" in c.lower() or "nombre" in c.lower()), None)
        cols_per = ["dni"]
        if col_nom_per: cols_per.append(col_nom_per)
        master_df = df_per[cols_per].copy()
        
        # B. Jalamos la Sede de Datos Generales
        if not df_gen.empty and "sede" in df_gen.columns:
            master_df = master_df.merge(df_gen[["dni", "sede"]], on="dni", how="left")
        else:
            master_df["sede"] = "No registrada" 
            
        # C. Unimos con los Contratos
        cols_cont = ["dni", "estado", "tipo de trabajador", "modalidad", "temporalidad", "tipo contrato", "cargo", "f_inicio", "f_fin"]
        cols_cont_existentes = [c for c in cols_cont if c in df_ultimos_contratos.columns]
        master_df = master_df.merge(df_ultimos_contratos[cols_cont_existentes], on="dni", how="left")

        # =====================================
        # FILTROS DE BÚSQUEDA
        # =====================================
        st.markdown("### 🔍 Filtros de Búsqueda")
        
        col_est, col_sede = st.columns(2)
        with col_est:
            f_estado = st.multiselect("Estado del Trabajador", options=master_df["estado"].dropna().unique(), default=["ACTIVO"])
        with col_sede:
            # Opciones fijas para que siempre aparezcan
            sedes_opciones = ["Local Giraldez", "Local San Carlos", "Local Abancay", "Local Lince", "Local Pueblo Libre"]
            f_sede = st.multiselect("Sede", options=sedes_opciones)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            f_ttrab = st.multiselect("Tipo de Trabajador", options=master_df.get("tipo de trabajador", pd.Series([], dtype=str)).dropna().unique())
            f_sexo = st.multiselect("Sexo", options=master_df.get("sexo", pd.Series([], dtype=str)).dropna().unique())
        with col2:
            f_mod = st.multiselect("Modalidad", options=master_df.get("modalidad", pd.Series([], dtype=str)).dropna().unique())
            f_ecivil = st.multiselect("Estado Civil", options=master_df.get("estado civil", pd.Series([], dtype=str)).dropna().unique())
        with col3:
            f_temp = st.multiselect("Temporalidad", options=master_df.get("temporalidad", pd.Series([], dtype=str)).dropna().unique())
        with col4:
            f_tcont = st.multiselect("Tipo de Contrato", options=master_df.get("tipo contrato", pd.Series([], dtype=str)).dropna().unique())

        # =====================================
        # APLICAR FILTROS
        # =====================================
        df_filtrado = master_df.copy()
        
        if f_estado: df_filtrado = df_filtrado[df_filtrado["estado"].isin(f_estado)]
        if f_sede and "sede" in df_filtrado.columns: df_filtrado = df_filtrado[df_filtrado["sede"].isin(f_sede)]
        if f_ttrab and "tipo de trabajador" in df_filtrado.columns: df_filtrado = df_filtrado[df_filtrado["tipo de trabajador"].isin(f_ttrab)]
        if f_sexo and "sexo" in df_filtrado.columns: df_filtrado = df_filtrado[df_filtrado["sexo"].isin(f_sexo)]
        if f_mod and "modalidad" in df_filtrado.columns: df_filtrado = df_filtrado[df_filtrado["modalidad"].isin(f_mod)]
        if f_ecivil and "estado civil" in df_filtrado.columns: df_filtrado = df_filtrado[df_filtrado["estado civil"].isin(f_ecivil)]
        if f_temp and "temporalidad" in df_filtrado.columns: df_filtrado = df_filtrado[df_filtrado["temporalidad"].isin(f_temp)]
        if f_tcont and "tipo contrato" in df_filtrado.columns: df_filtrado = df_filtrado[df_filtrado["tipo contrato"].isin(f_tcont)]
      
        # =====================================
        # MOSTRAR TABLA LIMPIA Y ORDENADA
        # =====================================
        st.markdown("---")
        st.success(f"📋 **Resultados:** Se encontraron **{len(df_filtrado)}** trabajadores.")
        
        cols_ideales = ["dni", col_nom_per, "sede", "cargo", "f_inicio", "f_fin", "estado"]
        cols_mostrar = [c for c in cols_ideales if c and c in df_filtrado.columns]
        
        df_display = df_filtrado[cols_mostrar].copy()
        
        # Forzamos el nombre a "Trabajador"
        df_display.rename(columns={
            "dni": "DNI",
            col_nom_per: "Trabajador",
            "sede": "Sede",
            "cargo": "Puesto Laboral",
            "f_inicio": "Inicio Contrato",
            "f_fin": "Fin Contrato",
            "estado": "Estado"
        }, inplace=True)
        
        # TABLA: Ajustada al contenido
        st.dataframe(df_display, hide_index=True, use_container_width=False)
        
        # BOTÓN DE EXPORTAR A EXCEL (REPORTE GENERAL)
        output_gen = BytesIO()
        with pd.ExcelWriter(output_gen, engine='openpyxl') as writer:
            df_display.to_excel(writer, index=False, sheet_name='General')
        st.download_button(
            label="📥 Exportar a Excel", 
            data=output_gen.getvalue(), 
            file_name="Reporte_General.xlsx", 
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
            key="btn_exp_gen",
            type="primary"
        )
    else:
        st.warning("⚠️ Necesitas tener datos registrados en Personal y Contratos para generar reportes.")
