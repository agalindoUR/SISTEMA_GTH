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

    # 1. Preparar la base (DNI y Nombres Completos)
    df_per_calc = df_per.copy()
    df_per_calc.columns = [str(c).upper().strip() for c in df_per_calc.columns]
    
    col_dni_per = next((c for c in df_per_calc.columns if "DNI" in c or "DOC" in c), None)
    if not col_dni_per:
        st.error("⚠️ No se encontró la columna DNI en la tabla PERSONAL.")
        return

    df_per_calc["DNI"] = df_per_calc[col_dni_per].astype(str).str.strip().str.replace(".0", "", regex=False).str.zfill(8)
    
    # --- CONSTRUCCIÓN DE NOMBRES Y APELLIDOS COMBINADOS ---
    cols_per = df_per_calc.columns.tolist()
    col_nom = next((c for c in cols_per if c in ['NOMBRES', 'NOMBRE']), None)
    col_ape = next((c for c in cols_per if c in ['APELLIDOS', 'APELLIDO']), None)
    col_full = next((c for c in cols_per if c in ['TRABAJADOR', 'NOMBRES Y APELLIDOS', 'APELLIDOS Y NOMBRES', 'COLABORADOR', 'EMPLEADO']), None)

    def obtener_nombre_completo(row):
        a = str(row[col_ape]).strip() if col_ape and pd.notna(row[col_ape]) and str(row[col_ape]).lower() != 'nan' else ""
        n = str(row[col_nom]).strip() if col_nom and pd.notna(row[col_nom]) and str(row[col_nom]).lower() != 'nan' else ""
        
        if a and n:
            if a.upper() in n.upper(): return n
            if n.upper() in a.upper(): return a
            return f"{a} {n}".strip()
        if a: return a
        if n: return n
        if col_full and pd.notna(row[col_full]): return str(row[col_full]).strip()
        return "SIN NOMBRE"

    df_per_calc["TRABAJADOR"] = df_per_calc.apply(obtener_nombre_completo, axis=1)
    df_rep = df_per_calc[["DNI", "TRABAJADOR"]].copy()
    
    # 2. Obtener SEDE (De Datos Generales)
    if not df_gen.empty:
        df_g_calc = df_gen.copy()
        df_g_calc.columns = [str(c).upper().strip() for c in df_g_calc.columns]
        col_dni_gen = next((c for c in df_g_calc.columns if "DNI" in c or "DOC" in c), "DNI")
        if col_dni_gen in df_g_calc.columns:
            df_g_calc["DNI"] = df_g_calc[col_dni_gen].astype(str).str.strip().str.replace(".0", "", regex=False).str.zfill(8)
            if "SEDE" in df_g_calc.columns:
                df_rep = df_rep.merge(df_g_calc[["DNI", "SEDE"]].drop_duplicates("DNI"), on="DNI", how="left")
    
    # 3. Obtener AREA, CARGO y ESTADO (De Contratos - Tomando el más reciente)
    if not df_cont.empty:
        df_c_calc = df_cont.copy()
        df_c_calc.columns = [str(c).upper().strip().replace("Á", "A") for c in df_c_calc.columns]
        col_dni_cont = next((c for c in df_c_calc.columns if "DNI" in c or "DOC" in c), "DNI")
        
        if col_dni_cont in df_c_calc.columns:
            df_c_calc["DNI"] = df_c_calc[col_dni_cont].astype(str).str.strip().str.replace(".0", "", regex=False).str.zfill(8)
            
            col_area = next((c for c in df_c_calc.columns if "AREA" in c), None)
            col_cargo = next((c for c in df_c_calc.columns if "CARGO" in c or "PUESTO" in c), None)
            col_estado = next((c for c in df_c_calc.columns if "ESTADO" in c), None)
            
            df_latest_cont = df_c_calc.sort_index(ascending=False).drop_duplicates("DNI")
            
            cols_to_merge = ["DNI"]
            if col_area: 
                df_latest_cont = df_latest_cont.rename(columns={col_area: "AREA"})
                cols_to_merge.append("AREA")
            if col_cargo: 
                df_latest_cont = df_latest_cont.rename(columns={col_cargo: "CARGO"})
                cols_to_merge.append("CARGO")
            if col_estado: 
                df_latest_cont = df_latest_cont.rename(columns={col_estado: "ESTADO"})
                cols_to_merge.append("ESTADO")
                
            df_rep = df_rep.merge(df_latest_cont[cols_to_merge], on="DNI", how="left")
    
    # Limpiar columnas y forzar mayúsculas
    for col in ["SEDE", "AREA", "CARGO", "ESTADO"]:
        if col not in df_rep.columns: 
            df_rep[col] = "NO REGISTRADO"
        df_rep[col] = df_rep[col].fillna("NO REGISTRADO").astype(str).str.upper()
    
    # 4. FILTROS VISUALES
    st.markdown("### 🔍 Filtros")
    
    solo_activos = st.checkbox("✅ Mostrar solo trabajadores vigentes (Contrato Activo)", value=True)
    
    c1, c2 = st.columns(2)
    with c1:
        sedes = ["TODAS"] + sorted([str(x) for x in df_rep["SEDE"].unique() if str(x) != "NAN"])
        sel_sede = st.selectbox("SEDE", sedes)
    with c2:
        areas = ["TODAS"] + sorted([str(x) for x in df_rep["AREA"].unique() if str(x) != "NAN"])
        sel_area = st.selectbox("ÁREA", areas)

    if solo_activos:
        df_rep = df_rep[df_rep["ESTADO"].str.contains("ACTIVO|VIGENTE", na=False)]
    if sel_sede != "TODAS": df_rep = df_rep[df_rep["SEDE"] == sel_sede]
    if sel_area != "TODAS": df_rep = df_rep[df_rep["AREA"] == sel_area]
    
    saldos_finales = []
    
    # 5. Obtener Saldo de Vacaciones desde la ventana/tabla "VACACIONES"
    for dni in df_rep["DNI"]:
        dni_str = str(dni).strip()
        saldo_final = 0.0
        
        if not df_vac.empty:
            v_df = df_vac.copy()
            v_df.columns = [str(c).upper().strip() for c in v_df.columns]
            col_dni_v = next((c for c in v_df.columns if "DNI" in c or "DOC" in c), "DNI")
            
            if col_dni_v in v_df.columns:
                v_df["DNI"] = v_df[col_dni_v].astype(str).str.strip().str.replace(".0", "", regex=False).str.zfill(8)
                v_df_filtro = v_df[v_df["DNI"] == dni_str]
                
                if not v_df_filtro.empty:
                    # CASO A: Si la tabla ya tiene una columna de 'SALDO' o 'PENDIENTE'
                    col_saldo = next((c for c in v_df_filtro.columns if "SALDO" in c or "PENDIENTE" in c or "RESTANTE" in c), None)
                    
                    if col_saldo:
                        # Extrae el último saldo registrado para ese trabajador
                        saldos_num = pd.to_numeric(v_df_filtro[col_saldo], errors='coerce').dropna()
                        if not saldos_num.empty:
                            saldo_final = float(saldos_num.iloc[-1])
                    
                    # CASO B: Si la tabla tiene columnas separadas de Generados y Gozados
                    else:
                        col_gen = next((c for c in v_df_filtro.columns if "GENERADO" in c or "GANADO" in c), None)
                        col_goz = next((c for c in v_df_filtro.columns if "GOZADO" in c or "TOMADO" in c or "DIAS" in c), None)
                        
                        dias_gen = pd.to_numeric(v_df_filtro[col_gen], errors='coerce').sum() if col_gen else 0.0
                        dias_goz = pd.to_numeric(v_df_filtro[col_goz], errors='coerce').sum() if col_goz else 0.0
                        
                        saldo_final = dias_gen - dias_goz

        saldos_finales.append(round(saldo_final, 2))
    
    # 6. Agregar resultados y mostrar tabla
    df_rep["SALDO DE VACACIONES"] = saldos_finales
    
    st.success(f"📋 **Resultados:** {len(df_rep)} registros calculados con éxito.")
    
    columnas_mostrar = ["DNI", "TRABAJADOR", "CARGO", "SEDE", "AREA", "ESTADO", "SALDO DE VACACIONES"]
    st.dataframe(df_rep[columnas_mostrar], hide_index=True, use_container_width=True)
    
    # 7. Exportar a Excel
    output_vac = BytesIO()
    with pd.ExcelWriter(output_vac, engine='openpyxl') as writer:
        df_rep[columnas_mostrar].to_excel(writer, index=False, sheet_name='Saldos_Vacaciones')
    st.download_button(
        label="📥 Exportar a Excel", 
        data=output_vac.getvalue(), 
        file_name="Reporte_Saldos_Vacaciones.xlsx", 
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="btn_exp_vac_nuevo",
        type="primary"
    )
