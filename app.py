# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
from datetime import date
from io import BytesIO
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. CONFIGURACIÓN Y CONSTANTES ---
DB = "DB_SISTEMA_GTH.xlsx"
F_N = "MG. ARTURO JAVIER GALINDO MARTINEZ"
F_C = "JEFE DE GESTIÓN DEL TALENTO HUMANO"
TEXTO_CERT = "LA OFICINA DE GESTIÓN DE TALENTO HUMANO DE LA UNIVERSIDAD PRIVADA DE HUANCAYO “FRANKLIN ROOSEVELT”, CERTIFICA QUE:"
MOTIVOS_CESE = ["Término de contrato", "Renuncia", "Despido", "Mutuo acuerdo", "Fallecimiento", "Otros"]

# Estructura exacta de columnas según documento
COLUMNAS = {
    "PERSONAL": ["dni", "apellidos y nombres", "link"],
    "DATOS GENERALES": ["apellidos y nombres", "dni", "dirección", "link de dirección", "estado civil", "fecha de nacimiento", "edad"],
    "DATOS FAMILIARES": ["parentesco", "apellidos y nombres", "dni", "fecha de nacimiento", "edad", "estudios", "telefono"],
    "EXP. LABORAL": ["tipo de experiencia", "lugar", "puesto", "fecha inicio", "fecha de fin", "motivo cese"],
    "FORM. ACADEMICA": ["grado, titulo o especialización", "descripcion", "universidad", "año"],
    "INVESTIGACION": ["año publicación", "autor, coautor o asesor", "tipo de investigación publicada", "nivel de publicación", "lugar de publicación"],
    "CONTRATOS": ["id", "dni", "cargo", "sueldo", "f_inicio", "f_fin", "tipo", "tipo contrato", "temporalidad", "link", "estado", "motivo cese"],
    "VACACIONES": ["periodo", "fecha de inicio", "fecha de fin", "días generados", "días gozados", "saldo", "fecha de goce inicial", "fecha de goce final", "link"],
    "OTROS BENEFICIES": ["periodo", "tipo de beneficio", "link"],
    "MERITOS Y DEMERITOS": ["periodo", "merito o demerito", "motivo", "link"],
    "EVALUACION DEL DESEMPEÑO": ["periodo", "merito o demerito", "motivo", "link"],
    "LIQUIDACIONES": ["periodo", "firmo", "link"]
}

# --- 2. FUNCIONES DE DATOS ---
def load_all_data():
    if not os.path.exists(DB):
        with pd.ExcelWriter(DB) as w:
            for hoja, cols in COLUMNAS.items():
                pd.DataFrame(columns=cols).to_excel(w, sheet_name=hoja, index=False)
    dfs = {}
    with pd.ExcelFile(DB) as x:
        for hoja in COLUMNAS.keys():
            df = pd.read_excel(x, hoja) if hoja in x.sheet_names else pd.DataFrame(columns=COLUMNAS[hoja])
            # NORMALIZACIÓN CRÍTICA: Convertir columnas a minúsculas y quitar espacios
            df.columns = [str(c).strip().lower() for c in df.columns]
            if "dni" in df.columns:
                df["dni"] = df["dni"].astype(str).str.strip().replace(r'\.0$', '', regex=True)
            dfs[hoja] = df
    return dfs

def save_all_data(dfs):
    with pd.ExcelWriter(DB) as w:
        for hoja, df in dfs.items():
            df_save = df.copy()
            df_save.columns = [c.upper() for c in df_save.columns]
            df_save.to_excel(w, sheet_name=hoja, index=False)

def gen_word_cert(nom, dni, df_c):
    doc = Document()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("CERTIFICADO DE TRABAJO")
    r.bold = True; r.font.name = 'Arial'; r.font.size = Pt(24) #
    doc.add_paragraph("\n" + TEXTO_CERT).alignment = WD_ALIGN_PARAGRAPH.JUSTIFY #
    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p2.add_run(f"El TRABAJADOR ").add_run(nom).bold = True
    p2.add_run(f", identificado con DNI N° {dni}, laboró en nuestra Institución bajo el siguiente detalle:") #
    t = doc.add_table(rows=1, cols=3); t.style = 'Table Grid'
    for i, h in enumerate(["CARGO", "FECHA INICIO", "FECHA FIN"]): t.rows[0].cells[i].text = h #
    for _, row in df_c.iterrows():
        c = t.add_row().cells
        c[0].text = str(row.get('cargo', ''))
        c[1].text = pd.to_datetime(row.get('f_inicio')).strftime('%d/%m/%Y') if pd.notnull(row.get('f_inicio')) else ""
        c[2].text = pd.to_datetime(row.get('f_fin')).strftime('%d/%m/%Y') if pd.notnull(row.get('f_fin')) else ""
    doc.add_paragraph("\n\nHuancayo, " + date.today().strftime("%d de %B de %Y")).alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f = doc.add_paragraph(); f.alignment = WD_ALIGN_PARAGRAPH.CENTER
    f.add_run("\n\n\n__________________________\n" + F_N + "\n" + F_C).bold = True #
    b = BytesIO(); doc.save(b); b.seek(0); return b

# --- 3. INTERFAZ Y LOGIN ---
st.set_page_config(page_title="GTH Roosevelt", layout="wide")
if "rol" not in st.session_state: st.session_state.rol = None

if st.session_state.rol is None:
    st.markdown("<h2 style='text-align:center;'>UNIVERSIDAD ROOSEVELT - SISTEMA GTH</h2>", unsafe_allow_html=True)
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"): #
        if u.lower() == "admin": st.session_state.rol = "Admin"
        elif u.lower() == "supervisor" and p == "123": st.session_state.rol = "Supervisor"
        elif u.lower() == "lector" and p == "123": st.session_state.rol = "Lector"
        else: st.error("Acceso denegado")
        if st.session_state.rol: st.rerun()
else:
    dfs = load_all_data()
    es_lector = st.session_state.rol == "Lector"
    
    m = st.sidebar.radio("MENÚ", ["🔍 Consulta", "➕ Registro", "📊 Verificar"])
    if st.sidebar.button("Cerrar Sesión"): st.session_state.rol = None; st.rerun()

    if m == "🔍 Consulta":
        dni_c = st.text_input("Consultar DNI del colaborador:").strip()
        if dni_c:
            p_data = dfs["PERSONAL"][dfs["PERSONAL"]["dni"] == dni_c]
            if not p_data.empty:
                nom_c = p_data.iloc[0]["apellidos y nombres"]
                st.header(f"👤 {nom_c}")
                
                # Organización por grupos
                st.subheader("Presentados por el trabajador")
                pest_trab = ["Datos Generales", "Exp. Laboral", "Form. Académica", "Investigación", "Datos Familiares"]
                tabs_t = st.tabs(pest_trab)
                
                st.subheader("Documentos internos")
                pest_int = ["Contratos", "Vacaciones", "Otros Beneficios", "Méritos/Demer.", "Evaluación", "Liquidaciones"]
                tabs_i = st.tabs(pest_int)
                
                all_tabs = tabs_t + tabs_i
                all_hojas = ["DATOS GENERALES", "EXP. LABORAL", "FORM. ACADEMICA", "INVESTIGACION", "DATOS FAMILIARES", 
                             "CONTRATOS", "VACACIONES", "OTROS BENEFICIOS", "MERITOS Y DEMERITOS", "EVALUACION DEL DESEMPEÑO", "LIQUIDACIONES"]

                for i, tab in enumerate(all_tabs
