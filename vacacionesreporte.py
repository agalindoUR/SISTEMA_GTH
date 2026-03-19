 # ==========================================
 # MÓDULO: REPORTE DE SALDO DE VACACIONES
 # ==========================================

import streamlit as st
import pandas as pd
from datetime import date
from io import BytesIO

def mostrar(dfs):
    st.markdown("<h2 style='color: #4A0000;'>🏖️ Reporte de Saldo de Vacaciones</h2>", unsafe_allow_html=True)
    
    df_per = dfs.get("PERSONAL", pd.DataFrame())
    df_gen = dfs.get("DATOS GENERALES", pd.DataFrame())
    df_cont = dfs.get("CONTRATOS", pd.DataFrame())
    df_vac = dfs.get("VACACIONES", pd.DataFrame())
    
    if df_per.empty:
        st.warning("⚠️ Faltan datos en Personal para generar este reporte.")
    else:
        # 1. Preparar la base (DNI y Nombres)
        df_per_calc = df_per.copy()
        df_per_calc.columns = [str(c).upper().strip() for c in df_per_calc.columns]
        df_per_calc["DNI"] = df_per_calc["DNI"].astype(str).str.strip().str.replace(".0", "", regex=False).str.zfill(8)
        col_n_p = next((c for c in df_per_calc.columns if "APELLIDO" in c or "NOMBRE" in c), "TRABAJADOR")
        
        df_rep = df_per_calc[["DNI", col_n_p]].copy()
        
        # 2. Obtener SEDE (De Datos Generales)
        if not df_gen.empty:
            df_g_calc = df_gen.copy()
            df_g_calc.columns = [str(c).upper().strip() for c in df_g_calc.columns]
            df_g_calc["DNI"] = df_g_calc["DNI"].astype(str).str.strip().str.replace(".0", "", regex=False).str.zfill(8)
            if "SEDE" in df_g_calc.columns:
                df_rep = df_rep.merge(df_g_calc[["DNI", "SEDE"]].drop_duplicates("DNI"), on="DNI", how="left")
        
        # 3. Obtener AREA (De Contratos - Tomando el más reciente)
        if not df_cont.empty:
            df_c_calc = df_cont.copy()
            # Quitamos tildes a las columnas por si acaso dice "ÁREA"
            df_c_calc.columns = [str(c).upper().strip().replace("Á", "A") for c in df_c_calc.columns]
            df_c_calc["DNI"] = df_c_calc["DNI"].astype(str).str.strip().str.replace(".0", "", regex=False).str.zfill(8)
            
            if "AREA" in df_c_calc.columns:
                # Sort index descending asume que los últimos agregados están al final, así tomamos el área actual
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
        
        # 5. Cálculo del Saldo de Vacaciones para los DNI filtrados
        for dni in df_rep["DNI"]:
            dni_str = str(dni).strip()
            dias_generados_totales = 0
            dias_gozados_totales = 0
            
            # --- A. Dias Gozados ---
            if not df_vac.empty:
                v_df = df_vac.copy()
                v_df.columns = [str(c).upper().strip() for c in v_df.columns]
                v_df["DNI"] = v_df["DNI"].astype(str).str.strip().str.replace(".0", "", regex=False).str.zfill(8)
                v_df_filtro = v_df[v_df["DNI"] == dni_str]
                
                if not v_df_filtro.empty:
                    col_goz = next((c for c in v_df_filtro.columns if "GOZADO" in c), None)
                    if col_goz:
                        dias_gozados_totales = pd.to_numeric(v_df_filtro[col_goz], errors='coerce').sum()

            # --- B. Días Generados (Contratos Planilla) ---
            if not df_cont.empty:
                c_df = df_cont.copy()
                c_df.columns = [str(c).upper().strip() for c in c_df.columns]
                c_df["DNI"] = c_df["DNI"].astype(str).str.strip().str.replace(".0", "", regex=False).str.zfill(8)
                c_df_filtro = c_df[c_df["DNI"] == dni_str]
                
                if not c_df_filtro.empty and "TIPO CONTRATO" in c_df_filtro.columns:
                    df_tc = c_df_filtro[c_df_filtro["TIPO CONTRATO"].astype(str).str.upper().str.contains("PLANILLA", na=False)]
                    
                    if not df_tc.empty and "F_INICIO" in df_tc.columns:
                        df_tc['F_INICIO_DT'] = pd.to_datetime(df_tc['F_INICIO'], errors='coerce')
                        start_global = df_tc['F_INICIO_DT'].min()
                        
                        if pd.notnull(start_global):
                            curr_start = start_global.date()
                            while curr_start <= date.today():
                                curr_end = (pd.to_datetime(curr_start) + pd.DateOffset(years=1) - pd.Timedelta(days=1)).date()
                                days_in_p = 0
                                for _, r in df_tc.iterrows():
                                    c_s = r['F_INICIO_DT'].date() if pd.notnull(r['F_INICIO_DT']) else None
                                    c_e_val = r.get('F_FIN')
                                    c_e = pd.to_datetime(c_e_val, errors='coerce').date() if pd.notnull(c_e_val) else date.today()
                                    
                                    if c_s:
                                        o_s, o_e = max(curr_start, c_s), min(curr_end, c_e, date.today())
                                        if o_s <= o_e: days_in_p += (o_e - o_s).days + 1
                                
                                total_days = (curr_end - curr_start).days + 1
                                gen_p = (days_in_p / total_days) * 30
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
