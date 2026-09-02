 # ==========================================
# MÓDULO: REPORTE DE SALDO DE VACACIONES
# ==========================================

import streamlit as st
import pandas as pd
from datetime import date, datetime
from io import BytesIO

def limpiar_fecha(val, fecha_defecto=None):
    """Convierte de forma segura cualquier tipo de dato a datetime.date."""
    if pd.isna(val) or str(val).strip() in ["", "-", "nan", "NaT", "None"]:
        return fecha_defecto
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()
    try:
        dt = pd.to_datetime(val, errors='coerce')
        return dt.date() if pd.notna(dt) else fecha_defecto
    except:
        return fecha_defecto

def mostrar(dfs):
    st.markdown("<h2 style='color: #4A0000;'>🏖️ Reporte de Saldo de Vacaciones</h2>", unsafe_allow_html=True)
    
    df_per = dfs.get("PERSONAL", pd.DataFrame())
    df_gen = dfs.get("DATOS GENERALES", pd.DataFrame())
    df_cont = dfs.get("CONTRATOS", pd.DataFrame())
    df_vac = dfs.get("VACACIONES", pd.DataFrame())
    
    if df_per.empty:
        st.warning("⚠️ Faltan datos en Personal para generar este reporte.")
        return

    # 1. Preparar la base (DNI y Nombres)
    df_per_calc = df_per.copy()
    df_per_calc.columns = [str(c).upper().strip() for c in df_per_calc.columns]
    
    col_dni_per = next((c for c in df_per_calc.columns if "DNI" in c or "DOC" in c), None)
    if not col_dni_per:
        st.error("⚠️ No se encontró la columna DNI en la tabla PERSONAL.")
        return

    df_per_calc["DNI"] = df_per_calc[col_dni_per].astype(str).str.strip().str.replace(".0", "", regex=False).str.zfill(8)
    col_n_p = next((c for c in df_per_calc.columns if "APELLIDO" in c or "NOMBRE" in c or "TRABAJADOR" in c), "TRABAJADOR")
    
    df_rep = df_per_calc[["DNI", col_n_p]].copy()
    
    # 2. Obtener SEDE (De Datos Generales)
    if not df_gen.empty:
        df_g_calc = df_gen.copy()
        df_g_calc.columns = [str(c).upper().strip() for c in df_g_calc.columns]
        col_dni_gen = next((c for c in df_g_calc.columns if "DNI" in c or "DOC" in c), "DNI")
        if col_dni_gen in df_g_calc.columns:
            df_g_calc["DNI"] = df_g_calc[col_dni_gen].astype(str).str.strip().str.replace(".0", "", regex=False).str.zfill(8)
            if "SEDE" in df_g_calc.columns:
                df_rep = df_rep.merge(df_g_calc[["DNI", "SEDE"]].drop_duplicates("DNI"), on="DNI", how="left")
    
    # 3. Obtener AREA (De Contratos - Tomando el más reciente)
    if not df_cont.empty:
        df_c_calc = df_cont.copy()
        df_c_calc.columns = [str(c).upper().strip().replace("Á", "A") for c in df_c_calc.columns]
        col_dni_cont = next((c for c in df_c_calc.columns if "DNI" in c or "DOC" in c), "DNI")
        if col_dni_cont in df_c_calc.columns:
            df_c_calc["DNI"] = df_c_calc[col_dni_cont].astype(str).str.strip().str.replace(".0", "", regex=False).str.zfill(8)
            if "AREA" in df_c_calc.columns:
                df_area = df_c_calc.sort_index(ascending=False).drop_duplicates("DNI")[["DNI", "AREA"]]
                df_rep = df_rep.merge(df_area, on="DNI", how="left")
    
    # Limpiar columnas y forzar mayúsculas
    if "SEDE" not in df_rep.columns: df_rep["SEDE"] = "NO REGISTRADA"
    if "AREA" not in df_rep.columns: df_rep["AREA"] = "NO REGISTRADA"
    
    df_rep["SEDE"] = df_rep["SEDE"].fillna("NO REGISTRADA").astype(str).str.upper()
    df_rep["AREA"] = df_rep["AREA"].fillna("NO REGISTRADA").astype(str).str.upper()
    
    # 4. FILTROS VISUALES
    st.markdown("### 🔍 Filtros")
    c1, c2 = st.columns(2)
    with c1:
        sedes = ["TODAS"] + sorted([str(x) for x in df_rep["SEDE"].unique() if str(x) != "NAN"])
        sel_sede = st.selectbox("SEDE", sedes)
    with c2:
        areas = ["TODAS"] + sorted([str(x) for x in df_rep["AREA"].unique() if str(x) != "NAN"])
        sel_area = st.selectbox("AREA", areas)

    # Aplicar filtros
    if sel_sede != "TODAS": df_rep = df_rep[df_rep["SEDE"] == sel_sede]
    if sel_area != "TODAS": df_rep = df_rep[df_rep["AREA"] == sel_area]
    
    saldos_finales = []
    hoy = date.today()
    
    # 5. Cálculo del Saldo de Vacaciones para los DNI filtrados
    for dni in df_rep["DNI"]:
        dni_str = str(dni).strip()
        dias_generados_totales = 0.0
        dias_gozados_totales = 0.0
        
        # --- A. Días Gozados ---
        if not df_vac.empty:
            v_df = df_vac.copy()
            v_df.columns = [str(c).upper().strip() for c in v_df.columns]
            col_dni_v = next((c for c in v_df.columns if "DNI" in c or "DOC" in c), "DNI")
            if col_dni_v in v_df.columns:
                v_df["DNI"] = v_df[col_dni_v].astype(str).str.strip().str.replace(".0", "", regex=False).str.zfill(8)
                v_df_filtro = v_df[v_df["DNI"] == dni_str]
                
                if not v_df_filtro.empty:
                    col_goz = next((c for c in v_df_filtro.columns if "GOZADO" in c or "DIAS" in c), None)
                    if col_goz:
                        dias_gozados_totales = pd.to_numeric(v_df_filtro[col_goz], errors='coerce').sum()

        # --- B. Días Generados (Contratos Planilla) ---
        if not df_cont.empty:
            c_df = df_cont.copy()
            c_df.columns = [str(c).upper().strip() for c in c_df.columns]
            col_dni_c = next((c for c in c_df.columns if "DNI" in c or "DOC" in c), "DNI")
            if col_dni_c in c_df.columns:
                c_df["DNI"] = c_df[col_dni_c].astype(str).str.strip().str.replace(".0", "", regex=False).str.zfill(8)
                c_df_filtro = c_df[c_df["DNI"] == dni_str]
                
                col_tipo = next((c for c in c_df_filtro.columns if "TIPO" in c or "CONTRATO" in c), None)
                col_finic = next((c for c in c_df_filtro.columns if "INICIO" in c or "F_INICIO" in c), None)
                col_ffin = next((c for c in c_df_filtro.columns if "FIN" in c or "F_FIN" in c), None)
                
                if not c_df_filtro.empty and col_tipo and col_finic:
                    df_tc = c_df_filtro[c_df_filtro[col_tipo].astype(str).str.upper().str.contains("PLANILLA", na=False)].copy()
                    
                    if not df_tc.empty:
                        df_tc['F_INICIO_CLEAN'] = df_tc[col_finic].apply(lambda x: limpiar_fecha(x, None))
                        df_tc_valid = df_tc[df_tc['F_INICIO_CLEAN'].notnull()]
                        
                        if not df_tc_valid.empty:
                            start_global = min(df_tc_valid['F_INICIO_CLEAN'])
                            curr_start = start_global
                            
                            while curr_start <= hoy:
                                curr_end = (pd.to_datetime(curr_start) + pd.DateOffset(years=1) - pd.Timedelta(days=1)).date()
                                days_in_p = 0
                                
                                for _, r in df_tc_valid.iterrows():
                                    c_s = r['F_INICIO_CLEAN']
                                    c_e_val = r.get(col_ffin) if col_ffin else None
                                    c_e = limpiar_fecha(c_e_val, fecha_defecto=hoy)
                                    
                                    if c_s:
                                        o_s = max(curr_start, c_s)
                                        o_e = min(curr_end, c_e, hoy)
                                        if o_s <= o_e:
                                            days_in_p += (o_e - o_s).days + 1
                                
                                total_days = (curr_end - curr_start).days + 1
                                gen_p = (days_in_p / total_days) * 30.0
                                dias_generados_totales += gen_p
                                curr_start = (pd.to_datetime(curr_start) + pd.DateOffset(years=1)).date()
        
        # --- C. Saldo ---
        saldo = round(dias_generados_totales - dias_gozados_totales, 2)
        saldos_finales.append(saldo)
    
    # 6. Agregar resultados y mostrar
    df_rep["SALDO DE VACACIONES"] = saldos_finales
    df_rep.rename(columns={col_n_p: "TRABAJADOR"}, inplace=True)
    
    st.success(f"📋 **Resultados:** {len(df_rep)} registros calculados con éxito.")
    st.dataframe(df_rep[["DNI", "TRABAJADOR", "SEDE", "AREA", "SALDO DE VACACIONES"]], hide_index=True, use_container_width=True)
    
    # 7. Exportar a Excel
    output_vac = BytesIO()
    with pd.ExcelWriter(output_vac, engine='openpyxl') as writer:
        df_rep[["DNI", "TRABAJADOR", "SEDE", "AREA", "SALDO DE VACACIONES"]].to_excel(writer, index=False, sheet_name='Saldos_Vacaciones')
    st.download_button(
        label="📥 Exportar a Excel", 
        data=output_vac.getvalue(), 
        file_name="Reporte_Saldos_Vacaciones.xlsx", 
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="btn_exp_vac_nuevo",
        type="primary"
    )
