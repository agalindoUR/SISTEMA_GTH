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
MOTIVOS_CESE = ["Termino de contrato", "Renuncia", "Despido", "Mutuo acuerdo", "Fallecimiento", "Otros"]

# Definición exacta de columnas por hoja según tu documento
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

# --- 2. GESTIÓN DE SESIÓN Y LOGIN ---
def check_login():
    """Gestiona el inicio de sesión según"""
    if "rol" not in st.session_state:
        st.session_state.rol = None

    if st.session_state.rol is None:
        st.markdown("<h1 style='text-align: center;'>UNIVERSIDAD PRIVADA DE HUANCAYO FRANKLIN ROOSEVELT</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center;'>Bienvenido al sistema de gestión de base de datos de colaboradores</h3>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.info("Ingrese sus credenciales")
            user = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            
            if st.button("Ingresar"):
                # Lógica de credenciales
                if user.lower() == "admin": 
                    st.session_state.rol = "Admin"
                    st.rerun()
                elif user.lower() == "supervisor" and password == "123":
                    st.session_state.rol = "Supervisor"
                    st.rerun()
                elif user.lower() == "lector" and password == "123":
                    st.session_state.rol = "Lector"
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos")
        return False
    return True

# --- 3. FUNCIONES DE DATOS ---
def normalize_cols(df):
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df

def load():
    if not os.path.exists(DB):
        with pd.ExcelWriter(DB) as w:
            for hoja, cols in COLUMNAS.items():
                pd.DataFrame(columns=cols).to_excel(w, sheet_name=hoja, index=False)
    
    dfs = {}
    with pd.ExcelFile(DB) as x:
        for hoja in COLUMNAS.keys():
            if hoja in x.sheet_names:
                df = pd.read_excel(x, hoja)
                df = normalize_cols(df)
                # Asegurar columnas mínimas
                for c in COLUMNAS[hoja]:
                    if c not in df.columns: df[c] = None
                # Limpieza DNI
                if "dni" in df.columns:
                    df["dni"] = df["dni"].astype(str).str.strip().replace(r'\.0$', '', regex=True)
                dfs[hoja] = df
            else:
                dfs[hoja] = pd.DataFrame(columns=COLUMNAS[hoja])
    return dfs

def save(dfs):
    with pd.ExcelWriter(DB) as w:
        for hoja, df in dfs.items():
            df_save = df.copy()
            df_save.columns = [c.upper() for c in df_save.columns]
            df_save.to_excel(w, sheet_name=hoja, index=False)

# --- 4. GENERADOR WORD ---
def gen_doc(nom, dni, df_contratos):
    doc = Document()
    p_tit = doc.add_paragraph()
    p_tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_tit = p_tit.add_run("CERTIFICADO DE TRABAJO")
    run_tit.bold = True; run_tit.font.name = 'Arial'; run_tit.font.size = Pt(24)
    
    doc.add_paragraph("\n")
    p1 = doc.add_paragraph(TEXTO_CERT); p1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    doc.add_paragraph("\n")
    
    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p2.add_run("El TRABAJADOR "); p2.add_run(f"{nom}").bold = True
    p2.add_run(f", identificado con DNI N° {dni}, laboró en nuestra Institución bajo el siguiente detalle:")
    doc.add_paragraph("\n")
    
    table = doc.add_table(rows=1, cols=3); table.style = 'Table Grid'
    hdr = table.rows[0].cells; hdr[0].text = "CARGO"; hdr[1].text = "FECHA INICIO"; hdr[2].text = "FECHA FIN"
    
    for _, row in df_contratos.iterrows():
        cells = table.add_row().cells
        cells[0].text = str(row.get('cargo', ''))
        fi = pd.to_datetime(row.get('f_inicio')).strftime('%d/%m/%Y') if pd.notnull(row.get('f_inicio')) else ""
        ff = pd.to_datetime(row.get('f_fin')).strftime('%d/%m/%Y') if pd.notnull(row.get('f_fin')) else ""
        cells[1].text = fi; cells[2].text = ff

    doc.add_paragraph("\n\n")
    hoy = date.today()
    meses = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"]
    p_fec = doc.add_paragraph(f"Huancayo, {hoy.day} de {meses[hoy.month-1]} del {hoy.year}")
    p_fec.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    
    doc.add_paragraph("\n\n\n")
    p_fir = doc.add_paragraph(); p_fir.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_fir.add_run("__________________________\n")
    p_fir.add_run(f"{F_N}\n").bold = True
    p_fir.add_run(F_C).bold = True
    
    buf = BytesIO(); doc.save(buf); buf.seek(0); return buf

# --- 5. INTERFAZ PRINCIPAL ---
if check_login():
    st.set_page_config(page_title="GTH Roosevelt", layout="wide")
    dfs = load()
    
    # Sidebar
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c8/Logo_Universidad_Privada_de_Huancayo_Franklin_Roosevelt.png/320px-Logo_Universidad_Privada_de_Huancayo_Franklin_Roosevelt.png", width=100)
    st.sidebar.title(f"Usuario: {st.session_state.rol}")
    
    # Bloqueo de edición para Lectores
    es_lector = st.session_state.rol == "Lector"
    
    m = st.sidebar.radio("MENÚ", ["🔍 Consulta", "➕ Registro", "📊 Nómina"])
    
    if m == "🔍 Consulta":
        st.title("Consulta de Colaborador")
        dni_b = st.text_input("Ingrese DNI:", placeholder="Ej: 43076279").strip()
        
        if dni_b:
            df_p = dfs["PERSONAL"]
            if "dni" in df_p.columns and not df_p[df_p["dni"] == dni_b].empty:
                nom = df_p[df_p["dni"] == dni_b].iloc[0]["apellidos y nombres"]
                st.success(f"Colaborador: {nom}")
                
                # Definición de Pestañas
                pestanas = ["Datos Generales", "Exp. Laboral", "Form. Academica", "Investigacion", "Datos Familiares", 
                            "Contratos", "Vacaciones", "Otros Beneficios", "Meritos
