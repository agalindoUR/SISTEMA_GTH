# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
from datetime import date
from io import BytesIO
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. CONFIGURACIÓN ---
DB = "DB_SISTEMA_GTH.xlsx"
F_N = "MG. ARTURO JAVIER GALINDO MARTINEZ"
F_C = "JEFE DE GESTIÓN DEL TALENTO HUMANO"
TEXTO_CERT = "LA OFICINA DE GESTIÓN DE TALENTO HUMANO DE LA UNIVERSIDAD PRIVADA DE HUANCAYO “FRANKLIN ROOSEVELT”, CERTIFICA QUE:"

COLUMNAS = {
    "PERSONAL": ["dni", "apellidos y nombres", "link"],
    "DATOS GENERALES": ["apellidos y nombres", "dni", "direccion", "link direccion", "estado civil", "fecha nacimiento", "edad"],
    "DATOS FAMILIARES": ["parentesco", "apellidos y nombres", "dni", "fecha nacimiento", "edad", "estudios", "telefono"],
    "EXP. LABORAL": ["tipo experiencia", "lugar", "puesto", "fecha inicio", "fecha fin", "motivo cese"],
    "FORM. ACADEMICA": ["grado titulo", "descripcion", "universidad", "año"],
    "INVESTIGACION": ["año publicacion", "autor", "tipo investigacion", "nivel", "lugar"],
    "CONTRATOS": ["id", "dni", "cargo", "sueldo", "f_inicio", "f_fin", "tipo", "tipo contrato", "temporalidad", "link", "estado", "motivo cese"],
    "VACACIONES": ["periodo", "fecha inicio", "fecha fin", "dias generados", "dias gozados", "saldo", "goce inicio", "goce fin", "link"],
    "OTROS BENEFICIOS": ["periodo", "tipo beneficio", "link"],
    "MERITOS Y DEMERITOS": ["periodo", "merito o demerito", "motivo", "link"],
    "EVALUACION DEL DESEMPEÑO": ["periodo", "merito o demerito", "motivo", "link"],
    "LIQUIDACIONES": ["periodo", "firmo", "link"]
}

# --- 2. FUNCIONES DE DATOS ---
def load():
    if not os.path.exists(DB):
        with pd.ExcelWriter(DB) as w:
            for hoja, cols in COLUMNAS.items(): pd.DataFrame(columns=cols).to_excel(w, sheet_name=hoja, index=False)
    dfs = {}
    with pd.ExcelFile(DB) as x:
        for h in COLUMNAS.keys():
            df = pd.read_excel(x, h) if h in x.sheet_names else pd.DataFrame(columns=COLUMNAS[h])
            df.columns = [str(c).strip().lower() for c in df.columns]
            if "dni" in df.columns: df["dni"] = df["dni"].astype(str).str.strip().replace(r'\.0$', '', regex=True)
            dfs[h] = df
    return dfs

def save(dfs):
    with pd.ExcelWriter(DB) as w:
        for h, df in dfs.items():
            df_s = df.copy()
            df_s.columns = [c.upper() for c in df_s.columns]
            df_s.to_excel(w, sheet_name=h, index=False)

def gen_doc(nom, dni, df_c):
    doc = Document()
    p = doc.add_paragraph(); p.alignment = 1
    r = p.add_run("CERTIFICADO DE TRABAJO"); r.bold = True; r.font.name = 'Arial'; r.font.size = Pt(24)
    doc.add_paragraph("\n" + TEXTO_CERT)
    p2 = doc.add_paragraph(); p2.add_run("El TRABAJADOR "); p2.add_run(nom).bold = True
    p2.add_run(f", identificado con DNI N° {dni}, laboró en nuestra Institución bajo el siguiente detalle:")
    t = doc.add_table(rows=1, cols=3); t.style = 'Table Grid'
    for i, h in enumerate(["CARGO", "FECHA INICIO", "FECHA FIN"]): t.rows[0].cells[i].text = h
    for _, row in df_c.iterrows():
        c = t.add_row().cells
        c[0].text = str(row.get('cargo', ''))
        c[1].text = pd.to_datetime(row.get('f_inicio')).strftime('%d/%m/%Y') if pd.notnull(row.get('f_inicio')) else ""
        c[2].text = pd.to_datetime(row.get('f_fin')).strftime('%d/%m/%Y') if pd.notnull(row.get('f_fin')) else ""
    doc.add_paragraph("\n\nHuancayo, " + date.today().strftime("%d/%m/%Y")).alignment = 2
    f = doc.add_paragraph(); f.alignment = 1; f.add_run("\n\n\n__________________________\n" + F_N + "\n" + F_C).bold = True
    b = BytesIO(); doc.save(b); b.seek(0); return b

# --- 3. LOGIN Y APP ---
st.set_page_config(page_title="GTH Roosevelt", layout="wide")
if "rol" not in st.session_state: st.session_state.rol = None

if st.session_state.rol is None:
    st.markdown("<h2 style='text-align:center;'>UNIVERSIDAD ROOSEVELT - SISTEMA GTH</h2>", unsafe_allow_html=True)
    with st.container():
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            if u.lower() == "admin": st.session_state.rol = "Admin"
            elif u.lower() == "supervisor" and p == "123": st.session_state.rol = "Supervisor"
            elif u.lower() == "lector" and p == "123": st.session_state.rol = "Lector"
            else: st.error("Error de acceso")
            if st.session_state.rol: st.rerun()
else:
    dfs = load()
    es_lector = st.session_state.rol == "Lector"
    m = st.sidebar.radio("MENÚ", ["🔍 Consulta", "➕ Registro", "📊 Verificar"])
    if st.sidebar.button("Cerrar Sesión"): st.session_state.rol = None; st.rerun
