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
    
    if df_per.empty or df_cont.empty:
        st.warning("⚠️ Faltan datos en PERSONAL o CONTRATOS para generar este reporte.")
        return

    # ==========================================
    # 1. PREPARAR CONTRATOS Y FILTRAR VIGENTES
    # ==========================================
    df_c_calc = df_cont.copy()
    df_c_calc.columns = [str(c).upper().strip().replace("Á", "A") for c in df_c_calc.columns]
    col_dni_cont = next((c for c in df_c_calc.columns if "DNI" in c or "DOC" in c), "DNI")
    
    df_c_calc["DNI"] = df_c_calc[col_dni_cont].astype(str).str.strip().str.replace(".0", "", regex=False).str.zfill(8)
    
    # Identificar columnas clave en contratos
    col_cargo = next((c for c in df_c_calc.columns if "CARGO" in c or "PUESTO" in c), "CARGO")
    col_area = next((c for c in df_c_calc.columns if "AREA" in c), "AREA")
    col_estado = next((c for c in df_c_calc.columns if "ESTADO" in c or "EST" in c), "ESTADO")
    col_tipo = next((c for c in df_c_calc.columns if "TIPO" in c or "CONTRATO" in c), "TIPO_CONTRATO")
    col_finic = next((c for c in df_c_calc.columns if "INICIO" in c or "F_INICIO" in c), "F_INICIO")
    col_ffin = next((c for c in df_c_calc.columns if "FIN" in c or "F_FIN" in c), "F_FIN")
    
    # Estandarizar estado y obtener SOLO LOS ACTIVOS para el listado principal
    if col_estado in df_c_calc.columns:
        df_c_calc[col_estado] = df_c_calc[col_estado].astype(str).str.upper()
        df_activos = df_c_calc[df_c_calc[col_estado].str.contains("ACT", na=False)]
    else:
        df_activos = df_c_calc.copy()

    # Obtener el registro del contrato activo (para jalar Cargo y Área actual)
    df_latest_cont = df_activos.drop_duplicates("DNI", keep="last")
    
    # ==========================================
    # 2. PREPARAR PERSONAL (NOMBRES EXACTOS)
    # ==========================================
    df_per_calc = df_per.copy()
    df_per_calc.columns = [str(c).upper().strip() for c in df_per_calc.columns]
    
    col_dni_per = next((c for c in df_per_calc.columns if "DNI" in c or "DOC" in c), "DNI")
    df_per_calc["DNI"] = df_per_calc[col_dni_per].astype(str).str.strip().str.replace(".0", "", regex=False).str.zfill(8)
    
    # FORZAR NOMBRES COMPLETOS: Apellidos + Nombres
    if "APELLIDOS Y NOMBRES" in df_per_calc.columns:
        df_per_calc["TRABAJADOR"] = df_per_calc["APELLIDOS Y NOMBRES"].astype(str).str.replace("nan", "", case=False)
    else:
        col_a = next((c for c in df_per_calc.columns if c in ['APELLIDOS', 'APELLIDO']), None)
        col_n = next((c for c in df_per_calc.columns if c in ['NOMBRES', 'NOMBRE']), None)
        
        apellidos = df_per_calc[col_a].astype(str).str.replace("nan", "", case=False) if col_a else ""
        nombres = df_per_calc[col_n].astype(str).str.replace("nan", "", case=False) if col_n else ""
        
        df_per_calc["TRABAJADOR"] = (apellidos + " " + nombres).str.strip()

    # ==========================================
    # 3. CRUZAR DATOS (SOLO VIGENTES)
    # ==========================================
    cols_base = ["DNI", "TRABAJADOR"]
    if "SEDE" in df_per_calc.columns:
        cols_base.append("SEDE")
        
    df_rep = df_per_calc[cols_base].copy()
    
    # Inner join con contratos activos: Esto ELIMINA automáticamente a los cesados
    cols_to_merge = ["DNI"]
    if col_cargo in df_latest_cont.columns: cols_to_merge.append(col_cargo)
    if col_area in df_latest_cont.columns: cols_to_merge.append(col_area)
    
    df_rep = df_rep.merge(df_latest_cont[cols_to_merge], on="DNI", how="inner")
    
    # Renombrar para asegurar estándar en pantalla
    df_rep = df_rep.rename(columns={col_cargo: "CARGO", col_area: "AREA"})

    # Limpieza de nulos
    for col in ["SEDE", "AREA", "CARGO"]:
        if col not in df_rep.columns: 
            df_rep[col] = "NO REGISTRADO"
        df_rep[col] = df_rep[col].fillna("NO REGISTRADO").astype(str).str.upper()

    # ==========================================
    # 4. FILTROS VISUALES
    # ==========================================
    st.markdown("### 🔍 Filtros")
    
    c1, c2 = st.columns(2)
    with c1:
        sedes = ["TODAS"] + sorted([str(x) for x in df_rep["SEDE"].unique() if str(x) != "NAN"])
        sel_sede = st.selectbox("SEDE", sedes)
    with c2:
        areas = ["TODAS"] + sorted([str(x) for x in df_rep["AREA"].unique() if str(x) != "NAN"])
        sel_area = st.selectbox("ÁREA", areas)

    if sel_sede != "TODAS": df_rep = df_rep[df_rep["SEDE"] == sel_sede]
    if sel_area != "TODAS": df_rep = df_rep[df_rep["AREA"] == sel_area]
    
    # ==========================================
    # 5. CÁLCULO INTEGRADO DE VACACIONES
    # ==========================================
    saldos_finales = []
    hoy = date.today()

    for dni in df_rep["DNI"]:
        dni_str = str(dni).strip()
        dias_generados_totales = 0.0
        dias_gozados_totales = 0.0

        # A. Días Gozados (Pestaña Vacaciones)
        if not df_vac.empty:
            v_df = df_vac.copy()
            v_df.columns = [str(c).upper().strip() for c in v_df.columns]
            col_dni_v = next((c for c in v_df.columns if "DNI" in c or "DOC" in c), "DNI")
            if col_dni_v in v_df.columns:
                v_df["DNI"] = v_df[col_dni_v].astype(str).str.strip().str.replace(".0", "", regex=False).str.zfill(8)
                v_df_filtro = v_df[v_df["DNI"] == dni_str]
                
                if not v_df_filtro.empty:
                    col_goz = next((c for c in v_df_filtro.columns if "GOZADO" in c or "DIAS" in c or "TOMADO" in c), None)
                    if col_goz:
                        dias_gozados_totales = pd.to_numeric(v_df_filtro[col_goz], errors='coerce').sum()

        # B. Días Generados (Todos los contratos acumulados del trabajador)
        c_df_filtro = df_c_calc[df_c_calc["DNI"] == dni_str].copy()
        
        if not c_df_filtro.empty and col_finic in c_df_filtro.columns:
            # Excluir Recibos por Honorarios
            if col_tipo in c_df_filtro.columns:
                c_df_filtro = c_df_filtro[~c_df_filtro[col_tipo].astype(str).str.upper().str.contains("HONORARIO|RXH", na=False)]
            
            for _, r in c_df_filtro.iterrows():
                f_inicio = limpiar_fecha(r[col_finic], None)
                f_fin_val = r.get(col_ffin) if col_ffin in c_df_filtro.columns else None
                f_fin = limpiar_fecha(f_fin_val, fecha_defecto=hoy)
                
                if f_inicio:
                    f_corte = min(f_fin, hoy)
                    if f_inicio <= f_corte:
                        dias_trabajados = (f_corte - f_inicio).days + 1
                        dias_generados_totales += (dias_trabajados / 365.0) * 30.0

        saldo = round(dias_generados_totales - dias_gozados_totales, 2)
        saldos_finales.append(max(0.0, saldo))

    # ==========================================
    # 6. MOSTRAR RESULTADOS
    # ==========================================
    df_rep["SALDO DE VACACIONES"] = saldos_finales
    
    st.success(f"📋 **Resultados:** {len(df_rep)} trabajadores vigentes procesados.")
    
    # Se añade la columna CARGO que faltaba visualizar
    columnas_mostrar = ["DNI", "TRABAJADOR", "CARGO", "SEDE", "AREA", "SALDO DE VACACIONES"]
    st.dataframe(df_rep[columnas_mostrar], hide_index=True, use_container_width=True)
    
    # EXPORTACIÓN
    output_vac = BytesIO()
    with pd.ExcelWriter(output_vac, engine='openpyxl') as writer:
        df_rep[columnas_mostrar].to_excel(writer, index=False, sheet_name='Saldos_Vacaciones')
    st.download_button(
        label="📥 Exportar a Excel", 
        data=output_vac.getvalue(), 
        file_name="Reporte_Saldos_Vacaciones.xlsx", 
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="btn_exp_vac_v3",
        type="primary"
    )
