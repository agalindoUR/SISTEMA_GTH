#==========================================

# MÓDULO: VENCIMIENTO DE CONTRATOS

# ==========================================

import streamlit as st
import pandas as pd
from io import BytesIO

def mostrar(dfs):
    st.markdown("<h2 style='color: #4A0000;'>⏳ Reporte de Vencimiento de Contratos</h2>", unsafe_allow_html=True)
    
    df_per = dfs.get("PERSONAL", pd.DataFrame())
    df_cont = dfs.get("CONTRATOS", pd.DataFrame())
    df_gen = dfs.get("DATOS GENERALES", pd.DataFrame())
    
    if not df_per.empty and not df_cont.empty:
        # 1. Base: DNI y Nombres Completos
        df_venc = df_per.copy()
        
        # Buscamos las columnas exactas de apellidos y nombres
        col_ape = next((c for c in df_venc.columns if "apellido" in c.lower()), None)
        col_nom = next((c for c in df_venc.columns if "nombre" in c.lower()), None)
        
        # Juntamos ambas columnas con un espacio en el medio
        if col_ape and col_nom:
            # Usamos fillna("") para evitar errores si hay celdas vacías
            df_venc["Nombre Completo"] = df_venc[col_ape].fillna("").astype(str) + " " + df_venc[col_nom].fillna("").astype(str)
        elif col_ape:
            df_venc["Nombre Completo"] = df_venc[col_ape]
        else:
            df_venc["Nombre Completo"] = "Desconocido"
            
        # Nos quedamos solo con el DNI y la nueva columna combinada
        cols_per = ["dni", "Nombre Completo"]
        df_venc = df_venc[cols_per]
        
        # 2. Sede (de Datos Generales)
        if not df_gen.empty and "sede" in df_gen.columns:
            df_venc = df_venc.merge(df_gen[["dni", "sede"]], on="dni", how="left")
        else:
            df_venc["sede"] = "No registrada"
            
        # 3. Datos del último contrato
        df_cont_sorted = df_cont.assign(f_fin_dt=pd.to_datetime(df_cont['f_fin'], errors='coerce')).sort_values('f_fin_dt')
        df_ultimos_contratos = df_cont_sorted.groupby('dni').tail(1)
        
        cols_cont_necesarias = ["dni", "cargo", "area", "f_fin", "tipo de trabajador", "tipo contrato"]
        cols_existentes = [c for c in cols_cont_necesarias if c in df_ultimos_contratos.columns]
        
        # Unimos solo los que tienen contrato
        df_venc = df_venc.merge(df_ultimos_contratos[cols_existentes], on="dni", how="inner") 
        
        # 4. Formatear la fecha y extraer el Mes
        df_venc["f_fin_dt"] = pd.to_datetime(df_venc["f_fin"], errors="coerce")
        meses_dict = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
        df_venc["Mes de Vencimiento"] = df_venc["f_fin_dt"].dt.month.map(meses_dict)
        
        # Renombrar para que se vea bien (AQUÍ USAMOS "Nombre Completo")
        rename_dict = {
            "dni": "DNI",
            "Nombre Completo": "Trabajador", 
            "sede": "Sede",
            "cargo": "Puesto",
            "AREA": "AREA",
            "f_fin": "Fecha de Vencimiento",
            "tipo de trabajador": "Tipo de Trabajador",
            "tipo contrato": "Tipo de Contrato"
        }
        df_venc.rename(columns=rename_dict, inplace=True)

        # =========================================================
        # NUEVO: ALERTA DE VENCIMIENTOS (PRÓXIMOS 30 DÍAS)
        # =========================================================
        hoy = pd.to_datetime('today').normalize() # Toma la fecha de hoy sin horas
        limite_30_dias = hoy + pd.Timedelta(days=30)

        # Filtramos usando la columna de fecha que ya creaste arriba (f_fin_dt)
        df_alerta = df_venc[(df_venc['f_fin_dt'] >= hoy) & (df_venc['f_fin_dt'] <= limite_30_dias)]

        if not df_alerta.empty:
            cantidad = len(df_alerta)
            st.warning(f"⚠️ **¡ATENCIÓN!** Tienes **{cantidad}** contrato(s) que vencen en los próximos 30 días.")
            
            with st.expander("👀 Ver detalle de los contratos por vencer"):
                cols_alerta = ["DNI", "Trabajador", "Puesto", "Fecha de Vencimiento"]
                cols_disp = [c for c in cols_alerta if c in df_venc.columns]
                st.dataframe(df_alerta[cols_disp], use_container_width=True, hide_index=True)
        else:
            st.success("✅ **¡Todo al día!** No tienes contratos próximos a vencer en los siguientes 30 días.")
            
        st.markdown("---")
        # =========================================================

        # 5. Filtros de Búsqueda
        col1, col2, col3 = st.columns(3)
        with col1:
            sedes_opciones = ["Local Giraldez", "Local San Carlos", "Local Abancay", "Local Lince", "Local Pueblo Libre"]
            f_sede = st.multiselect("Sede", options=sedes_opciones)
            areas_disp = df_venc["AREA"].dropna().unique() if "AREA" in df_venc.columns else []
            f_area = st.multiselect("AREA", options=areas_disp)
        with col2:
            f_mes = st.multiselect("Mes de Vencimiento", options=list(meses_dict.values()))
            tipos_trab = df_venc["Tipo de Trabajador"].dropna().unique() if "Tipo de Trabajador" in df_venc.columns else []
            f_ttrab = st.multiselect("Tipo de Trabajador", options=tipos_trab)
        with col3:
            tipos_cont = df_venc["Tipo de Contrato"].dropna().unique() if "Tipo de Contrato" in df_venc.columns else []
            f_tcont = st.multiselect("Tipo de Contrato", options=tipos_cont)
            
        # 6. Aplicar filtros
        if f_sede and "Sede" in df_venc.columns: df_venc = df_venc[df_venc["Sede"].isin(f_sede)]
        if f_area and "area" in df_venc.columns: df_venc = df_venc[df_venc["AREA"].isin(f_area)]
        if f_mes and "Mes de Vencimiento" in df_venc.columns: df_venc = df_venc[df_venc["Mes de Vencimiento"].isin(f_mes)]
        if f_ttrab and "Tipo de Trabajador" in df_venc.columns: df_venc = df_venc[df_venc["Tipo de Trabajador"].isin(f_ttrab)]
        if f_tcont and "Tipo de Contrato" in df_venc.columns: df_venc = df_venc[df_venc["Tipo de Contrato"].isin(f_tcont)]
        
        # Ordenar por fecha más próxima a vencer
        df_venc = df_venc.sort_values(by="f_fin_dt", na_position="last")
        
        # 7. Mostrar la Tabla
        cols_finales = ["DNI", "Trabajador", "Puesto", "Sede", "AREA", "Tipo de Trabajador", "Tipo de Contrato", "Fecha de Vencimiento", "Mes de Vencimiento"]
        cols_mostrar = [c for c in cols_finales if c in df_venc.columns]
        
        df_final = df_venc[cols_mostrar].copy()
        
        st.markdown("---")
        st.success(f"📋 **Resultados:** {len(df_final)} contratos encontrados.")
        st.dataframe(df_final, hide_index=True, use_container_width=False)
        
        # 8. Botón Exportar a Excel
        output_venc = BytesIO()
        with pd.ExcelWriter(output_venc, engine='openpyxl') as writer:
            df_final.to_excel(writer, index=False, sheet_name='Vencimientos')
        st.download_button(
            label="📥 Exportar a Excel", 
            data=output_venc.getvalue(), 
            file_name="Reporte_Vencimientos.xlsx", 
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="btn_exp_venc",
            type="primary"
        )
    else:
        st.warning("⚠️ Faltan datos en Personal o Contratos para generar este reporte.")
