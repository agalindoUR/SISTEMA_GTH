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
            tbs = st.tabs([s.replace("_"," ").title() for s in SHS])
            
            with tbs[4]: # CONTRATOS
                cn = dfs["contratos"][dfs["contratos"]['dni'] == dni_b].reset_index(drop=True)
                vst = cn.drop(columns=['id','modalidad','tipo colaborador'], errors='ignore')
                vst.columns = [c.title() for c in vst.columns]
                st.dataframe(vst, use_container_width=True, hide_index=True)
                
                c1, c2 = st.columns(2)
                with c1:
                    with st.expander("➕ Agregar"):
                        with st.form("add_f"):
                            f_car, f_sue = st.text_input("Cargo"), st.number_input("Sueldo", 0.0)
                            f_tip = st.selectbox("Tipo", ["Administrativo", "Docente"])
                            f_est = st.selectbox("Estado", ["VIGENTE", "CESADO"])
                            f_mot = st.selectbox("Motivo", MOTIVOS) if f_est == "CESADO" else "Vigente"
                            if st.form_submit_button("Guardar"):
                                nid = dfs["contratos"]['id'].max() + 1 if not dfs["contratos"].empty else 1
                                nr = {"id":nid, "dni":dni_b, "cargo":f_car, "sueldo":f_sue, "tipo":f_tip, "estado":f_est, "motivo cese":f_mot, "f_inicio": date.today()}
                                dfs["contratos"] = pd.concat([dfs["contratos"], pd.DataFrame([nr])], ignore_index=True)
                                save(dfs); st.rerun()
                with c2:
                    if not cn.empty:
                        with st.expander("📝 Editar / Eliminar", expanded=True):
                            ops = {f"{r['cargo']} ({r['f_inicio']})": i for i, r in cn.iterrows()}
                            sel = st.selectbox("Seleccionar:", list(ops.keys()))
                            idx_r = ops[sel]
                            idx_d = dfs["contratos"][(dfs["contratos"]['dni']==dni_b) & (dfs["contratos"]['id']==cn.at[idx_r, 'id'])].index[0]
                            with st.form("ed_f"):
                                e_ca = st.text_input("Cargo", value=str(cn.at[idx_r, 'cargo']))
