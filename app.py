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

def load():
    if not os.path.exists(DB):
        p = pd.DataFrame(columns=["DNI", "Apellidos y Nombres"])
        c = pd.DataFrame(columns=["DNI", "Cargo", "Sueldo", "F_Inicio", "F_Fin", "Tipo", "Modalidad", "Temporalidad", "Link", "Estado", "Tipo Colaborador", "Tipo Contrato", "Motivo Cese"])
        return p, c
    with pd.ExcelFile(DB) as x:
        p, c = pd.read_excel(x, "PERSONAL"), pd.read_excel(x, "CONTRATOS")
    for df in [p, c]: df["DNI"] = df["DNI"].astype(str).str.strip()
    return p, c

def save(p, c):
    with pd.ExcelWriter(DB) as w:
        p.to_excel(w, "PERSONAL", index=False); c.to_excel(w, "CONTRATOS", index=False)

def gen_doc(nom, dni, df):
    doc = Document()
    t = doc.add_paragraph(); t.alignment = 1; r = t.add_run("CERTIFICADO DE TRABAJO"); r.bold = True; r.font.size = Pt(16)
    h = doc.add_paragraph(); h.alignment = 1; h.add_run(CAB).font.size = Pt(10)
    b = doc.add_paragraph(); b.alignment = 3
    # REDACCIÓN SOLICITADA
    b.add_run(f"\nEl TRABAJADOR {nom}, identificado con DNI {dni} laboró en nuestra Institución bajo el siguiente detalle:").font.size = Pt(11)
    tb = doc.add_table(rows=1, cols=3); tb.style = 'Table Grid'
    for i, v in enumerate(["Cargo", "Fecha Inicio", "Fecha Fin"]):
        ph = tb.rows[0].cells[i].paragraphs[0]; ph.alignment = 1; rn = ph.add_run(v); rn.bold = True
    for _, f in df.iterrows():
        rc = tb.add_row().cells
        rc[0].text, rc[1].text, rc[2].text = str(f.get('Cargo','')), str(f.get('F_Inicio','')), str(f.get('F_Fin',''))
    f_p = doc.add_paragraph(f"\nHuancayo, {date.today().day} de febrero del 2026"); f_p.alignment = 2
    sig = doc.add_paragraph(f"\n\n\n{F_N}\n{F_C}"); sig.alignment = 1
    for run in sig.runs: run.bold = True
    buf = BytesIO(); doc.save(buf); buf.seek(0); return buf

# --- INTERFAZ ---
st.set_page_config(page_title="GTH Roosevelt", layout="wide")
dp, dc = load()
st.sidebar.title("SISTEMA GTH")
m = st.sidebar.radio("MENÚ", ["🔍 Consulta", "➕ Registro", "📊 Nómina"])

if m == "🔍 Consulta":
    dni = st.text_input("DNI:").strip()
    if dni:
        u = dp[dp['DNI'] == dni]
        if not u.empty:
            nom = u.iloc[0]['Apellidos y Nombres']
            st.success(f"Trabajador: {nom}")
            cn = dc[dc['DNI'] == dni].reset_index(drop=True)
            # Tabla con todas las columnas [cite: image_ba63bc.

