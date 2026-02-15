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
            try: df = pd.read_excel(x, s)
            except: df = pd.DataFrame(columns=["DNI"])
            if "DNI" in df.columns: df["DNI"] = df["DNI"].astype(str).str.strip()
            df.columns = [col.strip().lower() for col in df.columns]
            dict_dfs[s] = df
    return dict_dfs

def save_all(dict_dfs):
    with pd.ExcelWriter(DB) as w:
        for s, df in dict_dfs.items():
            df.to_excel(w, sheet_name=s, index=False)

def gen_doc(nom, dni, df):
    doc = Document()
    t = doc.add_paragraph(); t.alignment = 1; r = t.add_run("CERTIFICADO DE TRABAJO"); r.bold = True; r.font.size = Pt(16)
    h = doc.add_paragraph(); h.alignment = 1; h.add_run(CAB).font.size = Pt(10)
    b = doc.add_paragraph(); b.alignment = 3
    b.add_run(f"\nEl TRABAJADOR {nom}, identificado con DNI {dni} laboró en nuestra Institución bajo el siguiente detalle:").font.size = Pt(11)
    tb = doc.add_table(rows=1, cols=3); tb.style = 'Table Grid'
    for i, v in enumerate(["Cargo", "Fecha Inicio", "Fecha Fin"]):
        ph = tb.rows[0].cells[i].paragraphs[0]; ph.alignment = 1; rn = ph.add_run(v); rn.bold = True
    for _, f in df.iterrows():
        rc = tb.add_row().cells
        rc[0].text, rc[1].text, rc[2].text = str(f.get('cargo','')), str(f.get('f_inicio','')), str(f.get('f_fin',''))
    f_p = doc.add_paragraph(f"\nHuancayo, {date.today().day} de febrero del 2026"); f_p.alignment = 2
    sig = doc.add_paragraph(f"\n\n\n{F_N}\n{F_C}"); sig.alignment = 1
    for run in sig.runs: run.bold = True
    buf = BytesIO(); doc.save(buf); buf.seek(0); return buf

# --- INTERFAZ ---
st.set_page_config(page_title="GTH Roosevelt", layout="wide")
dfs = load()
st.sidebar.title("SISTEMA GTH")
m = st.sidebar.radio("MENÚ", ["🔍 Consulta", "➕ Registro Nuevo", "📊 Nómina"])

if m == "🔍 Consulta":
    dni_b = st.text_input("Ingrese DNI:").strip()
    if dni_b:
        u = dfs["PERSONAL"][dfs["PERSONAL"]['dni'] == dni_b]
        if not u.empty:
            nom = u.iloc[0]['apellidos y nombres']
            st.header(f"👤 {nom}")
            tabs = st.tabs(["Datos Generales", "Familia", "Form. Acad.", "Exp. Laboral", "Contratos", "Vacaciones", "Beneficios", "Méritos", "Liquidaciones"])
            
            with tabs[4]: # PESTAÑA CONTRATOS
                st.write("### Historial de Contratos")
                cn = dfs["CONTRATOS"][dfs["CONTRATOS"]['dni'] == dni_b].reset_index(drop=True)
                st.dataframe(cn.drop(columns=['id', 'tipo colaborador'], errors='ignore'), use_container_width=True, hide_index=True)
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    with st.expander("➕ Agregar"):
                        with st.form("f_add"):
                            n_car = st.text_input("Cargo")
                            n_sue = st.number_input("Sueldo", min_value=0.0)
                            n_est = st.selectbox("Estado", ["VIGENTE", "CESADO"])
                            n_mot = "
