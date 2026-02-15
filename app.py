# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
from datetime import date
from io import BytesIO
from docx import Document

# --- CONFIGURACIÓN ---
DB = "DB_SISTEMA_GTH.xlsx"
F_N, F_C = "MG. ARTURO J. GALINDO MARTINEZ", "JEFE DE GESTIÓN DE TALENTO HUMANO"
MOTIVOS = ["Termino de contrato", "Renuncia", "Despido", "Mutuo acuerdo", "Fallecimiento", "Otros"]
SHS = ["PERSONAL", "FAMILIA", "FORM_ACAD", "EXP_LABORAL", "CONTRATOS", "VACACIONES", "BENEFICIOS", "MERITOS", "LIQUIDACIONES"]

def load():
    if not os.path.exists(DB):
        with pd.ExcelWriter(DB) as w:
            for s in SHS: pd.DataFrame(columns=["dni"]).to_excel(w, sheet_name=s, index=False)
    dfs = {}
    with pd.ExcelFile(DB) as x:
        for s in SHS:
            df = pd.read_excel(x, s) if s in x.sheet_names else pd.DataFrame(columns=["dni"])
            df.columns = [c.strip().lower() for c in df.columns]
            if "dni" in df.columns: df["dni"] = df["dni"].astype(str).str.strip()
            dfs[s.lower()] = df
    return dfs

def save(dfs):
    with pd.ExcelWriter(DB) as w:
        for s in SHS: dfs[s.lower()].to_excel(w, sheet_name=s, index=False)

# --- INTERFAZ ---
st.set_page_config(page_title="GTH Roosevelt", layout="wide")
dfs = load()

st.sidebar.title("SISTEMA GTH")
m = st.sidebar.radio("MENÚ", ["🔍 Consulta", "➕ Registro", "📊 Nómina"])

if m == "🔍 Consulta":
    dni_b = st.text_input("DNI:").strip()
    if dni_b:
        u = dfs["personal"][dfs["personal"]['dni'] == dni_b]
        if not u.empty:
            nom = u.iloc[0]['apellidos y nombres']
            st.header(f"👤 {nom}")
            # Títulos de pestañas con Mayúscula Inicial
            tbs = st.tabs([s.replace("_"," ").title() for s in SHS])
            
            with tbs[4]: # PESTAÑA CONTRATOS
                st.write("### Gestión de Contratos")
                cn = dfs["contratos"][dfs["contratos"]['dni'] == dni_b].reset_index(drop=True)
                
                # Vista de tabla con columnas en Mayúscula inicial
                vista = cn.drop(columns=['id','modalidad','tipo colaborador'], errors='ignore')
                vista.columns = [c.title() for c in vista.columns]
                st.dataframe(vista, use_container_width=True, hide_index=True)
                
                c1, c2 = st.columns(2)
                with c1:
                    with st.expander("➕ Agregar Nuevo Contrato"):
                        with st.form("add_f"):
                            f_car = st.text_input("Cargo")
                            f_sue = st.number_input("Sueldo", 0.0)
                            f_tip = st.selectbox("Tipo", ["Administrativo", "Docente"])
                            f_tem = st.selectbox("Temporalidad", ["Plazo fijo", "Indeterminado"])
                            f_est = st.selectbox("Estado", ["VIGENTE", "CESADO"])
                            f_mot = st.selectbox("Motivo Cese", MOTIVOS) if f_est == "CESADO" else "Vigente"
                            if st.form_submit_button("Guardar Contrato"):
                                nid = dfs["contratos"]['id'].max() + 1 if not dfs["contratos"].empty else 1
                                nr = {"id":nid, "dni":dni_b, "cargo":f_car, "sueldo":f_sue, "tipo":f_tip, 
                                      "temporalidad":f_tem, "estado":f_est, "motivo cese":f_mot, "f_inicio": date.today()}
                                dfs["contratos"] = pd.concat([dfs["contratos"], pd.DataFrame([nr])], ignore_index=True)
                                save(dfs); st.rerun()

                with c2:
                    if not cn.empty:
                        with st.expander("📝 Editar / 🗑️ Eliminar Contrato", expanded=True):
                            # Selector manual para evitar el error de selección de tabla
                            opciones_edit = {f"{r['cargo']} ({r['f_inicio']})": i for i, r in cn.iterrows()}
                            sel_label = st.selectbox("Seleccione contrato para gestionar:", list(opciones_edit.keys()))
                            idx_real = opciones_edit[sel_label]
                            
                            # Buscar el índice original en el DataFrame principal
                            idx_db = dfs["contratos"][(dfs["contratos"]['dni']==dni_b) & (dfs["contratos"]['id']==cn.at[idx_real, 'id'])].index[0]
                            
                            with st.form("edit_f"):
                                e_car = st.text_input("Cargo", value=str(cn.at[idx_real, 'cargo']))
                                e_sue = st.number_input("Sueldo", value=float(cn.at[idx_real, 'sueldo']))
                                e_tip = st.text_input("Tipo", value=str(cn.at[idx_real, 'tipo']))
                                e_tem = st.text_input("Temporalidad", value=str(cn.at[idx_real, 'temporalidad']))
                                e_est = st.selectbox("Estado", ["VIGENTE", "CESADO"], index=0 if cn.at[idx_real, 'estado']=="VIGENTE" else 1)
                                e_mot = st.selectbox("Motivo Cese", MOTIVOS, index=MOTIVOS.index(cn.at[idx_real, 'motivo cese']) if cn.at[idx_real, 'motivo cese'] in MOTIVOS else 0) if e_est == "CESADO" else "Vigente"
                                
                                b1, b2 = st.columns(2)
                                if b1.form_submit
