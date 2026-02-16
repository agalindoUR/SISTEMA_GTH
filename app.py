# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
from datetime import date
from io import BytesIO
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# =========================================================
# --- 1. CONFIGURACIÓN, CONSTANTES Y DATOS DEL FIRMANTE ---
# =========================================================
DB = "DB_SISTEMA_GTH.xlsx"
F_N = "MG. ARTURO JAVIER GALINDO MARTINEZ"
F_C = "JEFE DE GESTIÓN DEL TALENTO HUMANO"
TEXTO_CERT = "LA OFICINA DE GESTIÓN DE TALENTO HUMANO DE LA UNIVERSIDAD PRIVADA DE HUANCAYO “FRANKLIN ROOSEVELT”, CERTIFICA QUE:"
MOTIVOS_CESE = ["Término de contrato", "Renuncia", "Despido", "Mutuo acuerdo", "Fallecimiento", "Otros"]

COLUMNAS = {
    "PERSONAL": ["dni", "apellidos y nombres", "link"],
    "DATOS GENERALES": ["apellidos y nombres", "dni", "dirección", "link de dirección", "estado civil", "fecha de nacimiento", "edad"],
    "DATOS FAMILIARES": ["parentesco", "apellidos y nombres", "dni", "fecha de nacimiento", "edad", "estudios", "telefono"],
    "EXP. LABORAL": ["tipo de experiencia", "lugar", "puesto", "fecha inicio", "fecha de fin", "motivo cese"],
    "FORM. ACADEMICA": ["grado, titulo o especialización", "descripcion", "universidad", "año"],
    "INVESTIGACION": ["año publicación", "autor, coautor o asesor", "tipo de investigación publicada", "nivel de publicación", "lugar de publicación"],
    "CONTRATOS": ["id", "dni", "cargo", "sueldo", "f_inicio", "f_fin", "tipo", "estado", "motivo cese"],
    "VACACIONES": ["periodo", "fecha de inicio", "fecha de fin", "días generados", "días gozados", "saldo", "link"],
    "OTROS BENEFICIOS": ["periodo", "tipo de beneficio", "link"],
    "MERITOS Y DEMERITOS": ["periodo", "merito o demerito", "motivo", "link"],
    "EVALUACION DEL DESEMPEÑO": ["periodo", "merito o demerito", "motivo", "link"],
    "LIQUIDACIONES": ["periodo", "firmo", "link"]
}

# =========================================================
# --- 2. FUNCIONES DE BASE DE DATOS ---
# =========================================================
def load_data():
    if not os.path.exists(DB):
        with pd.ExcelWriter(DB) as w:
            for h, cols in COLUMNAS.items(): pd.DataFrame(columns=cols).to_excel(w, sheet_name=h, index=False)
    dfs = {}
    with pd.ExcelFile(DB) as x:
        for h in COLUMNAS.keys():
            df = pd.read_excel(x, h) if h in x.sheet_names else pd.DataFrame(columns=COLUMNAS[h])
            df.columns = [str(c).strip().lower() for c in df.columns]
            if "dni" in df.columns:
                df["dni"] = df["dni"].astype(str).str.strip().replace(r'\.0$', '', regex=True)
            dfs[h] = df
    return dfs

def save_data(dfs):
    with pd.ExcelWriter(DB) as w:
        for h, df in dfs.items():
            df_s = df.copy()
            df_s.columns = [c.upper() for c in df_s.columns]
            df_s.to_excel(w, sheet_name=h, index=False)

# =========================================================
# --- 3. FUNCIÓN GENERADORA DEL CERTIFICADO (WORD) ---
# =========================================================
def gen_word(nom, dni, df_c):
    doc = Document()
    section = doc.sections[0]
    section.page_height = Inches(11.69); section.page_width = Inches(8.27)
    section.top_margin = Inches(1.6); section.bottom_margin = Inches(1.2)
    section.left_margin = Inches(1.0); section.right_margin = Inches(1.0)

    header = section.header
    section.header_distance = Inches(0)
    if os.path.exists("header.png"):
        p_h = header.paragraphs[0]
        p_h.paragraph_format.left_indent = Inches(-1.0) 
        p_h.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p_h.add_run().add_picture("header.png", width=Inches(8.27))

    footer = section.footer
    section.footer_distance = Inches(0)
    if os.path.exists("footer.png"):
        p_f = footer.paragraphs[0]
        p_f.paragraph_format.left_indent = Inches(-1.0)
        p_f.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p_f.add_run().add_picture("footer.png", width=Inches(8.27))

    p_tit = doc.add_paragraph()
    p_tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_tit = p_tit.add_run("CERTIFICADO DE TRABAJO")
    r_tit.bold = True; r_tit.font.name = 'Arial'; r_tit.font.size = Pt(24)

    doc.add_paragraph("\n" + TEXTO_CERT).alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_inf = doc.add_paragraph()
    p_inf.add_run("El TRABAJADOR ").bold = False
    p_inf.add_run(nom).bold = True
    p_inf.add_run(f", identificado con DNI N° {dni}, laboró bajo el siguiente detalle:")

    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    t = doc.add_table(rows=1, cols=3); t.style = 'Table Grid'; t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for i, h in enumerate(["CARGO", "FECHA INICIO", "FECHA FIN"]):
        cell = t.rows[0].cells[i]; r = cell.paragraphs[0].add_run(h); r.bold = True
        shd = OxmlElement('w:shd'); shd.set(qn('w:fill'), 'E1EFFF'); cell._tc.get_or_add_tcPr().append(shd)

    for _, fila in df_c.iterrows():
        celdas = t.add_row().cells
        celdas[0].text = str(fila.get('cargo', ''))
        celdas[1].text = pd.to_datetime(fila.get('f_inicio')).strftime('%d/%m/%Y') if pd.notnull(fila.get('f_inicio')) else ""
        celdas[2].text = pd.to_datetime(fila.get('f_fin')).strftime('%d/%m/%Y') if pd.notnull(fila.get('f_fin')) else ""

    doc.add_paragraph("\n\nHuancayo, " + date.today().strftime("%d/%m/%Y")).alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f = doc.add_paragraph(); f.alignment = WD_ALIGN_PARAGRAPH.CENTER
    f.add_run("\n\n__________________________\n" + F_N + "\n" + F_C).bold = True

    buf = BytesIO(); doc.save(buf); buf.seek(0)
    return buf

# =========================================================
# --- 4. INTERFAZ Y DISEÑO VISUAL (STREAMLIT) ---
# =========================================================
st.set_page_config(page_title="GTH Roosevelt", layout="wide")

st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #4a0000 0%, #800000 100%); }
    .login-header { color: white; text-align: center; font-size: 35px; font-weight: bold; text-shadow: 2px 2px 4px #000; }
    .login-welcome { color: #FFD700; text-align: center; font-size: 18px; margin-bottom: 30px; }
    label { color: white !important; font-size: 20px !important; font-weight: bold; }
    div[data-baseweb="input"] { width: 50% !important; margin: auto !important; }
    div.stButton > button { background-color: #FFD700 !important; color: #4a0000 !important; font-size: 22px !important; font-weight: bold !important; width: 50%; display: block; margin: auto; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

if "rol" not in st.session_state: st.session_state.rol = None

# --- LÓGICA DE LOGIN ---
if st.session_state.rol is None:
    st.markdown('<p class="login-header">UNIVERSIDAD ROOSEVELT - SISTEMA GTH</p>', unsafe_allow_html=True)
    st.markdown('<p class="login-welcome">Bienvenido (a) al sistema de gestión de datos de los colaboradores de la Universidad Roosevelt</p>', unsafe_allow_html=True)
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("INGRESAR"):
        if u.lower() == "admin": st.session_state.rol = "Admin"
        elif u.lower() == "supervisor" and p == "123": st.session_state.rol = "Supervisor"
        elif u.lower() == "lector" and p == "123": st.session_state.rol = "Lector"
        else: st.error("Acceso denegado")
        if st.session_state.rol: st.rerun()

# --- SISTEMA PRINCIPAL ---
else:
    dfs = load_data()
    es_lector = st.session_state.rol == "Lector"
    m = st.sidebar.radio("MENÚ", ["🔍 Consulta", "➕ Registro", "📊 Nómina General"])
    if st.sidebar.button("Cerrar Sesión"): st.session_state.rol = None; st.rerun()

    if m == "🔍 Consulta":
        dni_b = st.text_input("DNI del colaborador:").strip()
        if dni_b:
            pers = dfs["PERSONAL"][dfs["PERSONAL"]["dni"] == dni_b]
            if not pers.empty:
                nom_c = pers.iloc[0]["apellidos y nombres"]
                st.header(f"👤 {nom_c}")
                t_noms = ["Datos Generales", "Exp. Laboral", "Form. Académica", "Investigación", "Datos Familiares", "Contratos", "Vacaciones", "Otros Beneficios", "Méritos/Demer.", "Evaluación", "Liquidaciones"]
                h_keys = ["DATOS GENERALES", "EXP. LABORAL", "FORM. ACADEMICA", "INVESTIGACION", "DATOS FAMILIARES", "CONTRATOS", "VACACIONES", "OTROS BENEFICIOS", "MERITOS Y DEMERITOS", "EVALUACION DEL DESEMPEÑO", "LIQUIDACIONES"]
                tabs = st.tabs(t_noms
