# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
from datetime import date
from io import BytesIO
from docx import Document
from docx.shared import Pt

# --- CONFIGURACIÓN ---
DB = "DB_SISTEMA_GTH.xlsx"
F_N = "MG. ARTURO J. GALINDO MARTINEZ"
F_C = "JEFE DE GESTIÓN DE TALENTO HUMANO"
CAB = "LA OFICINA DE GESTIÓN DE TALENTO HUMANO DE LA UNIVERSIDAD PRIVADA DE HUANCAYO “FRANKLIN ROOSEVELT”, CERTIFICA QUE:"
MOTIVOS_CESE = ["Termino de contrato", "Renuncia", "Despido", "Mutuo acuerdo", "Fallecimiento", "Otros"]

def load():
    sheets = ["PERSONAL", "FAMILIA", "FORM_ACAD", "EXP_LABORAL", "CONTRATOS", "VACACIONES", "BENEFICIOS", "MERITOS", "LIQUIDACIONES"]
    if not os.path.exists(DB):
        with pd.ExcelWriter(DB) as w:
            for s in sheets: pd.DataFrame(columns=["DNI"]).to_excel(w, sheet_name=s, index=False)
        return {s: pd.DataFrame(columns=["DNI"]) for s in sheets}
    
    dict_dfs = {}
    with pd.ExcelFile(DB) as x:
        for s in sheets:
            try:
                df = pd.read_excel(x, s)
            except:
                df = pd.DataFrame(columns=["DNI"])
            if "DNI" in df.columns: df["DNI"] = df["DNI"].astype(str).str.strip()
            df.columns = [col.strip().lower() for col in df.columns]
            dict_dfs[s] = df
    return dict_dfs

def save_all(dict_dfs):
    with pd.ExcelWriter(DB) as w:
        for s, df in dict_dfs.items():
            df.to_excel(w, sheet_name=s, index=False)

# --- INTERFAZ ---
st.set_page_config(page_title="GTH Roosevelt - Legajo", layout="wide")
dfs = load()

st.sidebar.title("SISTEMA GTH")
m = st.sidebar.radio("MENÚ PRINCIPAL", ["🔍 Consulta de Legajo", "➕ Registro Nuevo Personal", "📊 Nómina General"])

if m == "🔍 Consulta de Legajo":
    dni_busq = st.text_input("Ingrese DNI del Colaborador:").strip()
    if dni_busq:
        u = dfs["PERSONAL"][dfs["PERSONAL"]['dni'] == dni_busq]
        if not u.empty:
            nom = u.iloc[0]['apellidos y nombres']
            st.header(f"👤 Colaborador: {nom}")
            
            t1, t2, t3, t4, t5, t6, t7, t8, t9 = st.tabs([
                "Datos Generales", "Familia", "Form. Acad.", "Exp. Laboral", 
                "Contratos", "Vacaciones", "Otros Beneficios", "Mérit. y Demer.", "Liquidaciones"
            ])

            with t1: 
                st.write("### Información Personal")
                st.table(u.drop(columns=['id'], errors='ignore'))
            
            with t2: 
                st.write("### Datos de Familia")
                st.dataframe(dfs["FAMILIA"][dfs["FAMILIA"]['dni'] == dni_busq], use_container_width=True)
                with st.expander("➕ Registrar Familiar"):
                    with st.form("f_fam"):
                        par = st.text_input("Parentesco / Nombre")
                        if st.form_submit_button("Guardar"):
                            dfs["FAMILIA"] = pd.concat([dfs["FAMILIA"], pd.DataFrame([{"dni":dni_busq, "familiar":par}])], ignore_index=True)
                            save_all(dfs); st.rerun()
            
            with t3: 
                st.write("### Formación Académica")
                st.dataframe(dfs["FORM_ACAD"][dfs["FORM_ACAD"]['dni'] == dni_busq], use_container_width=True)
            
            with t4: 
                st.write("### Experiencia Laboral")
                st.dataframe(dfs["EXP_LABORAL"][dfs["EXP_LABORAL"]['dni'] == dni_busq], use_container_width=True)

            with t5:
                st.write("### Gestión de Contratos")
                cn = dfs["CONTRATOS"][dfs["CONTRATOS"]['dni'] == dni_busq].reset_index(drop=True)
                # Ocultar ID y columnas duplicadas
                vista_c = cn.drop(columns=['id', 'tipo colaborador', 'link'], errors='ignore')
                st.dataframe(vista_c, use_container_width=True, hide_index=True)
                
                c_acc1, c_acc2, c_acc3 = st.columns(3)
                with c_acc1:
                    with st.expander("➕ Nuevo Contrato"):
                        with st.form("add_c"):
                            f_car = st.text_input("Cargo")
                            f_sue = st.number_input("Sueldo", min_value=0.0)
                            f_est = st.selectbox("Estado", ["VIGENTE", "CESADO"])
                            f_mot = "Vigente"
                            if f_est == "CESADO": f_mot = st.selectbox("Motivo de Cese", MOTIVOS_
