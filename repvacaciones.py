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
        st.warning("⚠️ Faltan datos en la hoja PERSONAL para generar este reporte.")
        return

    # 1. Preparar base desde PERSONAL (DNI, Apellidos y Nombres, Sede)
    df_per_calc = df_per.copy()
    df_per_calc.columns = [str(c).upper().strip() for c in df_per_calc.columns]
    
    col_dni_per = next((c for c in df_per_calc.columns if "DNI" in c or "DOC" in c), None)
    if not col_dni_per:
        st.error("⚠️ No se encontró la columna DNI en la tabla PERSONAL.")
        return

    df_per_calc["DNI"] = df_per_calc[col_dni_per].astype(str).str.strip().str.replace(".0", "", regex=False).str.zfill(8)
    
    # --- CONSTRUCCIÓN DE APELLIDOS Y NOMBRES ---
    col_ape = next((c for c in df_per_calc.columns if c in ['APELLIDOS', 'APELLIDO']), None)
    col_nom = next((c for c in df_per_calc.columns if c in ['NOMBRES', 'NOMBRE']), None)
    col_full = next((c for c in df_per_calc.columns if 'APELLIDOS Y NOMBRES' in c or 'TRABAJADOR' in c), None)

    def obtener_nombre_completo(row):
        a = str(row[col_ape]).strip() if col_ape and pd.notna(row[col_ape]) and str(row[col_ape]).lower() != 'nan' else ""
        n = str(row[col_nom]).strip() if col_nom and pd.notna(row[col_nom]) and str(row[col_nom]).lower() != 'nan' else ""
        if a and n:
            return f"{a}, {n}"
        if col_full and pd.notna(row[col_full]):
            return str(row[col_full]).strip()
        return a or n or "SIN NOMBRE"

    df_per_calc["TRABAJADOR"] = df_per_calc.apply(obtener_nombre_completo, axis=1)
    
    cols_base = ["DNI", "TRABAJADOR"]
    if "SEDE" in df_per_calc.columns:
        cols_base.append("SEDE")
        
    df_rep = df_per_calc[cols_base].copy()

    # 2. Obtener CARGO, AREA y ESTADO desde CONTRATOS
    if not df_cont.empty:
        df_c_calc = df_cont.copy()
        df_c_calc.columns = [str(c).upper().strip().replace("Á", "A") for c in df_c_calc.columns]
        col_dni_cont = next((c for c in df_c_calc.columns if "DNI" in c or "DOC" in c), "DNI")
        
        if col_dni_cont in df_c_calc.columns:
            df_c_calc["DNI"] = df_c_calc[col_dni_cont].astype(str).str.strip().str.replace(".0", "", regex=False).str.zfill(8)
            
            col_cargo = next((c for c in df_c_calc.columns if "CARGO" in c or "PUESTO" in c), None)
            col_area = next((c for c in df_c_calc.columns if "AREA" in c), None)
            col_estado = next((c for c in df_c_calc.columns if "ESTADO" in c or "EST" in c), None)
            
            # Tomamos el registro más reciente por DNI
            df_latest_cont = df_c_calc.sort_index(ascending=False).drop_duplicates("DNI")
            
            cols_to_merge = ["DNI"]
            if col_cargo: 
                df_latest_cont = df_latest_cont.rename(columns={col_cargo: "CARGO"})
                cols_to_merge.append("CARGO")
            if col_area and "AREA" not in df_rep.columns: 
                df_latest_cont = df_latest_cont.rename(columns={col_area: "AREA"})
                cols_to_merge.append("AREA")
            if col_estado: 
                df_latest_cont = df_latest_cont.rename(columns={col_estado: "ESTADO"})
                cols_to_merge.append("ESTADO")
                
            df_rep = df_rep.merge(df_latest_cont[cols_to_merge], on="DNI", how="left")

    # Limpieza general de valores nulos o no registrados
    for col in ["SEDE", "AREA", "CARGO", "ESTADO"]:
        if col not in df_rep.columns: 
            df_rep[col] = "NO REGISTRADO"
        df_rep[col] = df_rep[col].fillna("NO REGISTRADO").astype(str).str.upper()

    # 3. FILTROS VISUALES EN INTERFAZ
    st.markdown("### 🔍 Filtros")
    
    solo_activos = st.checkbox("✅ Mostrar solo trabajadores vigentes (Contrato Activo)", value=True)
    
    c1, c2 = st.columns(2)
    with c1:
        sedes = ["TODAS"] + sorted([str(x) for x in df_rep["SEDE"].unique() if str(x) != "NAN"])
        sel_sede = st.selectbox("SEDE", sedes)
    with c2:
        areas = ["TODAS"] + sorted([str(x) for x in df_rep["AREA"].unique() if str(x) != "NAN"])
        sel_area = st.selectbox("ÁREA", areas)

    # Aplicación de filtros
    if solo_activos:
        df_rep = df_rep[df_rep["ESTADO"].str.contains("ACT", na=False)]
    if sel_sede != "TODAS": 
        df_rep = df_rep[df_rep["SEDE"] == sel_sede]
    if sel_area != "TODAS": 
        df_rep = df_rep[df_rep["AREA"] == sel_area]
    
    saldos_finales = []
    hoy = date.today()

    # 4. CÁLCULO INTEGRADO DE VACACIONES (GENERADAS - GOZADAS)
    for dni in df_rep["DNI"]:
        dni_str = str(dni).strip()
        dias_generados_totales = 0.0
        dias_gozados_totales = 0.0

        # A. Días Gozados desde la pestaña VACACIONES (Lee acumulado si existen registros)
        if not df_vac.empty:
            v_df = df_vac.copy()
            v_df.columns = [str(c).upper().strip() for c in v_df.columns]
            col_dni_v = next((c for c in v_df.columns if "DNI" in c or "DOC" in c), "DNI")
            if col_dni_v in v_df.columns:
                v_df["DNI"] = v_df[col_dni_v].astype(str).str.strip().str.replace(".0", "", regex=False).str.zfill(8)
                v_df_filtro = v_df[v_df["DNI"] == dni_str]
                
                if not v_df_filtro.empty:
                    # Busca columnas como DIAS, DIAS GOZADOS, GOZADOS, CANTIDAD DIAS, etc.
                    col_goz = next((c for c in v_df_filtro.columns if "GOZADO" in c or "DIAS" in c or "TOMADO" in c or "CANTIDAD" in c), None)
                    if col_goz:
                        dias_gozados_totales = pd.to_numeric(v_df_filtro[col_goz], errors='coerce').sum()

        # B. Días Generados calculados desde la pestaña CONTRATOS
        if not df_cont.empty:
            c_df = df_cont.copy()
            c_df.columns = [str(c).upper().strip() for c in c_df.columns]
            col_dni_c = next((c for c in c_df.columns if "DNI" in c or "DOC" in c), "DNI")
            
            if col_dni_c in c_df.columns:
                c_df["DNI"] = c_df[col_dni_c].astype(str).str.strip().str.replace(".0", "", regex=False).str.zfill(8)
                c_df_filtro = c_df[c_df["DNI"] == dni_str].copy()
                
                col_tipo = next((c for c in c_df_filtro.columns if "TIPO" in c or "CONTRATO" in c), None)
                col_finic = next((c for c in c_df_filtro.columns if "INICIO" in c or "F_INICIO" in c), None)
                col_ffin = next((c for c in c_df_filtro.columns if "FIN" in c or "F_FIN" in c), None)
                
                if not c_df_filtro.empty and col_finic:
                    # Se excluyen los contratos por Recibo por Honorarios / RXH
                    if col_tipo:
                        c_df_filtro = c_df_filtro[~c_df_filtro[col_tipo].astype(str).str.upper().str.contains("HONORARIO|RXH", na=False)]
                    
                    for _, r in c_df_filtro.iterrows():
                        f_inicio = limpiar_fecha(r[col_finic], None)
                        f_fin_val = r.get(col_ffin) if col_ffin else None
                        f_fin = limpiar_fecha(f_fin_val, fecha_defecto=hoy)
                        
                        if f_inicio:
                            f_corte = min(f_fin, hoy)
                            if f_inicio <= f_corte:
                                dias_trabajados = (f_corte - f_inicio).days + 1
                                # 30 días de vacaciones por cada 365 días laborados
                                dias_generados_totales += (dias_trabajados / 365.0) * 30.0

        saldo = round(dias_generados_totales - dias_gozados_totales, 2)
        saldos_finales.append(max(0.0, saldo))

    # 5. MOSTRAR RESULTADOS
    df_rep["SALDO DE VACACIONES"] = saldos_finales
    
    st.success(f"📋 **Resultados:** {len(df_rep)} registros procesados con éxito.")
    
    columnas_mostrar = ["DNI", "TRABAJADOR", "CARGO", "SEDE", "AREA", "ESTADO", "SALDO DE VACACIONES"]
    st.dataframe(df_rep[columnas_mostrar], hide_index=True, use_container_width=True)
    
    # 6. EXPORTACIÓN A EXCEL
    output_vac = BytesIO()
    with pd.ExcelWriter(output_vac, engine='openpyxl') as writer:
        df_rep[columnas_mostrar].to_excel(writer, index=False, sheet_name='Saldos_Vacaciones')
    st.download_button(
        label="📥 Exportar a Excel", 
        data=output_vac.getvalue(), 
        file_name="Reporte_Saldos_Vacaciones.xlsx", 
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="btn_exp_vac_v2",
        type="primary"
    )
