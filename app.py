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
MOTIVOS = ["Termino de contrato", "Renuncia", "Despido", "Mutuo acuerdo", "Fallecimiento", "Otros"]

def load():
    shs = ["PERSONAL", "FAMILIA", "FORM_ACAD", "EXP_LABORAL", "CONTRATOS", "VACACIONES", "BENEFICIOS", "MERITOS", "LIQUIDACIONES"]
    if not os.path.exists(DB):
        with pd.ExcelWriter(DB) as w:
            for s in shs: pd.DataFrame(columns=["DNI"]).to_excel(w, sheet_name=s, index=False)
        return {s: pd.DataFrame(columns=["DNI"]) for s in shs}
    dfs = {}
    with pd.ExcelFile(DB) as x:
        for s in shs:
            try: df = pd.read_excel(x, s)
            except: df = pd.DataFrame(columns=["DNI"])
            if "DNI" in df.columns: df["DNI"] = df["DNI"].astype(str).str.strip()
            df.columns = [c.strip().lower() for c in df.columns]
            dfs[s] = df
    return dfs

def save_all(dfs):
    with pd.ExcelWriter(DB) as w:
        for s, df in dfs.items(): df.to_excel(w, sheet_name=s, index=False)

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
            tbs = st.tabs(["Datos Generales", "Familia", "Form. Acad.", "Exp. Laboral", "Contratos", "Vacaciones", "Beneficios", "Méritos", "Liquidaciones"])
            
            with tbs[4]: # PESTAÑA CONTRATOS
                st.write("### Gestión de Contratos")
                cn = dfs["CONTRATOS"][dfs["CONTRATOS"]['dni'] == dni_b].reset_index(drop=True)
                st.dataframe(cn.drop(columns=['id', 'tipo colaborador'], errors='ignore'), use_container_width=True, hide_index=True)
                c1, c2, c3 = st.columns(3)
                with c1:
                    with st.expander("➕ Agregar"):
                        with st.form("f1"):
                            car, sue = st.text_input("Cargo"), st.number_input("Sueldo", min_value=0.0)
                            est = st.selectbox("Estado", ["VIGENTE", "CESADO"])
                            mot = "Vigente"
                            if est == "CESADO": mot = st.selectbox("Motivo", MOTIVOS)
                            if st.form_submit_button("Guardar"):
                                nid = dfs["CONTRATOS"]['id'].max() + 1 if not dfs["CONTRATOS"].empty else 1
                                nr = {"id":nid, "dni":dni_b, "cargo":car, "sueldo":sue, "estado":est, "motivo cese":mot, "f_inicio": date.today()}
                                dfs["CONTRATOS"] = pd.concat([dfs["CONTRATOS"], pd.DataFrame([nr])], ignore_index=True)
                                save_all(dfs); st.rerun()
                with c2:
                    if not cn.empty:
                        with st.expander("📝 Editar"):
                            op = {f"{r['cargo']} ({r['f_inicio']})": r['id'] for _, r in cn.iterrows()}
                            sid = op[st.selectbox("Editar:", list(op.keys()))]
                            idx = dfs["CONTRATOS"][dfs["CONTRATOS"]['id'] == sid].index[0]
                            with st.form("f2"):
                                ns = st.number_input("Sueldo", value=float(dfs["CONTRATOS"].at[idx, 'sueldo']))
                                ne = st.selectbox("Estado", ["VIGENTE", "CESADO"])
                                if st.form_submit_button("Actualizar"):
                                    dfs["CONTRATOS"].at[idx
