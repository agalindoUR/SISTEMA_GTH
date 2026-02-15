# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
from datetime import date
from io import BytesIO

# --- CONFIGURACIÓN ---
DB = "DB_SISTEMA_GTH.xlsx"
F_N, F_C = "MG. ARTURO J. GALINDO MARTINEZ", "JEFE DE GESTIÓN DE TALENTO HUMANO"
MOTIVOS = ["Termino de contrato", "Renuncia", "Despido", "Mutuo acuerdo", "Fallecimiento", "Otros"]
SHS = ["PERSONAL", "FAMILIA", "FORM_ACAD", "EXP_LABORAL", "CONTRATOS", "VACACIONES", "BENEFICIOS", "MERITOS", "LIQUIDACIONES"]

def load():
    if not os.path.exists(DB):
        with pd.ExcelWriter(DB) as w:
            for s in SHS: pd.DataFrame(columns=["DNI", "NOMBRES"]).to_excel(w, sheet_name=s, index=False)
    dfs = {}
    with pd.ExcelFile(DB) as x:
        for s in SHS:
            df = pd.read_excel(x, s) if s in x.sheet_names else pd.DataFrame(columns=["dni"])
            # Normalizamos nombres de columnas para el motor interno
            df.columns = [str(c).strip().lower() for c in df.columns]
            if "dni" in df.columns: 
                df["dni"] = df["dni"].astype(str).str.strip().replace('\.0', '', regex=True)
            dfs[s.lower()] = df
    return dfs

def save(dfs):
    with pd.ExcelWriter(DB) as w:
        for s in SHS:
            # Al guardar, ponemos la primera letra en mayúscula para el Excel
            df_to_save = dfs[s.lower()].copy()
            df_to_save.columns = [str(c).capitalize() for c in df_to_save.columns]
            df_to_save.to_excel(w, sheet_name=s, index=False)

# --- INTERFAZ ---
st.set_page_config(page_title="GTH Roosevelt", layout="wide")
dfs = load()
st.sidebar.title("SISTEMA GTH")
m = st.sidebar.radio("MENÚ", ["🔍 Consulta", "➕ Registro", "📊 Nómina"])

if m == "🔍 Consulta":
    dni_b = st.text_input("Ingrese DNI para buscar:").strip()
    if dni_b:
        # Búsqueda insensible a tipos de datos
        p_df = dfs["personal"]
        u = p_df[p_df['dni'] == dni_b]
        
        if not u.empty:
            # Intentar obtener nombre de columnas comunes
            nom = u.iloc[0].get('apellidos y nombres', u.iloc[0].get('nombres', 'Trabajador'))
            st.header(f"👤 {nom}")
            
            tbs = st.tabs([s.replace("_"," ").title() for s in SHS])
            
            with tbs[4]: # PESTAÑA CONTRATOS
                st.subheader("Historial de Contratos")
                cn = dfs["contratos"][dfs["contratos"]['dni'] == dni_b].reset_index(drop=True)
                
                # Vista con Check de Selección
                vst = cn.copy()
                if 'id' in vst.columns: vst = vst.drop(columns=['id'])
                vst.columns = [c.title() for c in vst.columns]
                vst.insert(0, "Seleccionar", False)
                
                ed_df = st.data_editor(vst, use_container_width=True, hide_index=True, key="edit_cont")
                sel_idx = ed_df[ed_df["Seleccionar"] == True].index
                
                # SECCIÓN ELIMINAR (APARTE)
                if len(sel_idx) > 0:
                    st.warning("⚠️ Zona de Peligro")
                    if st.button("🚨 Eliminar Contrato Seleccionado"):
                        id_del = cn.at[sel_idx[0], 'id']
                        dfs["contratos"] = dfs["contratos"][dfs["contratos"]['id'] != id_del]
                        save(dfs); st.rerun()
                
                st.divider()
                
                # SECCIÓN AGREGAR Y EDITAR
                col1, col2 = st.columns([1, 2])
                with col1:
                    with st.expander("➕ Nuevo Contrato"):
                        with st.form("new_c"):
                            nc_car = st.text_input("Cargo")
                            nc_sue = st.number_input("Sueldo", 0.0)
                            nc_ini = st.date_input("Fecha Inicio")
                            if st.form_submit_button("Guardar"):
                                new_id = dfs["contratos"]['id'].max() + 1 if not dfs["contratos"].empty else 1
                                nr = {"id":new_id, "dni":dni_b, "cargo":nc_car, "sueldo":nc_sue, "f_inicio":nc_ini, "estado":"ACTIVO"}
                                dfs["contratos"] = pd.concat([dfs["contratos"], pd.DataFrame([nr])], ignore_index=True)
                                save(dfs); st.rerun()
                
                with col2:
                    if len(sel_idx) > 0:
                        i = sel_idx[0]
                        id_db = cn.at[i, 'id']
                        idx_db = dfs["contratos"][dfs["contratos"]['id'] == id_db].index[0]
                        
                        with st.expander("📝 Editar Contrato Seleccionado", expanded=True):
                            with st.form("edit_c"):
                                c_a, c_b = st.columns(2)
                                with c_a:
                                    e_car = st.text_input("Cargo", value=str(cn.at[i, 'cargo']))
                                    e_sue = st.number_input("Sueldo", value=float(cn.at[i, 'sueldo']))
                                    e_ini = st.date_input("Fecha Inicio", value=pd.to_datetime(cn.at[i, 'f_inicio']))
                                    e_fin = st.date_input("Fecha Fin", value=pd.to_datetime(cn.at[i].get('f_fin', date.today())))
                                with c_b:
                                    e_tip = st.text_input("Tipo", value=str(cn.at[i].get('tipo', '')))
                                    e_tem = st.text_input("Temporalidad", value=str(cn.at[i].get('temporalidad', '')))
                                    e_lnk = st.text_input("Link", value=str(cn.at[i].get('link', '')))
                                    e_tct
