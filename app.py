# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
from datetime import date
from io import BytesIO
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. CONFIGURACIÓN Y CONSTANTES ---
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

# --- 2. FUNCIONES DE DATOS Y CERTIFICADOS ---
def load_data():
    if not os.path.exists(DB):
        with pd.ExcelWriter(DB) as w:
            for h, cols in COLUMNAS.items():
                pd.DataFrame(columns=cols).to_excel(w, sheet_name=h, index=False)
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

def gen_word(nom, dni, df_c):
    doc = Document()
    section = doc.sections[0]
    section.page_height, section.page_width = Inches(11.69), Inches(8.27)
    section.top_margin, section.bottom_margin = Inches(1.6), Inches(1.2)
    
    header = section.header
    if os.path.exists("header.png"):
        p_h = header.paragraphs[0]
        p_h.paragraph_format.left_indent = Inches(-1.0)
        p_h.add_run().add_picture("header.png", width=Inches(8.27))

    footer = section.footer
    if os.path.exists("footer.png"):
        p_f = footer.paragraphs[0]
        p_f.paragraph_format.left_indent = Inches(-1.0)
        p_f.add_run().add_picture("footer.png", width=Inches(8.27))

    p_tit = doc.add_paragraph()
    p_tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_tit = p_tit.add_run("CERTIFICADO DE TRABAJO")
    r_tit.bold, r_tit.font.name, r_tit.font.size = True, 'Arial', Pt(24)

    doc.add_paragraph("\n" + TEXTO_CERT).alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_inf = doc.add_paragraph()
    p_inf.add_run("El TRABAJADOR ").bold = False
    p_inf.add_run(nom).bold = True
    p_inf.add_run(f", identificado con DNI N° {dni}, laboró bajo el siguiente detalle:")

    t = doc.add_table(rows=1, cols=3)
    t.style = 'Table Grid'
    for i, h in enumerate(["CARGO", "FECHA INICIO", "FECHA FIN"]):
        t.rows[0].cells[i].text = h

    for _, fila in df_c.iterrows():
        celdas = t.add_row().cells
        celdas[0].text = str(fila.get('cargo', ''))
        celdas[1].text = pd.to_datetime(fila.get('f_inicio')).strftime('%d/%m/%Y') if pd.notnull(fila.get('f_inicio')) else ""
        celdas[2].text = pd.to_datetime(fila.get('f_fin')).strftime('%d/%m/%Y') if pd.notnull(fila.get('f_fin')) else ""

    doc.add_paragraph("\n\nHuancayo, " + date.today().strftime("%d/%m/%Y")).alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f = doc.add_paragraph()
    f.alignment = WD_ALIGN_PARAGRAPH.CENTER
    f.add_run("\n\n__________________________\n" + F_N + "\n" + F_C).bold = True

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- 3. INTERFAZ Y LOGIN ---
st.set_page_config(page_title="GTH Roosevelt", layout="wide")

st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #4a0000 0%, #800000 100%); }
    .login-header { color: white; text-align: center; font-size: 42px; font-weight: bold; margin-top: 40px; }
    .login-welcome { color: #FFD700; text-align: center; font-size: 20px; margin-bottom: 20px; font-style: italic; }
    label { color: white !important; font-size: 22px !important; font-weight: bold !important; }
    div.stButton > button { 
        background-color: #FFD700 !important; color: #4a0000 !important; 
        font-size: 24px !important; font-weight: bold !important; width: 100%; height: 55px; border-radius: 12px; 
    }
    </style>
""", unsafe_allow_html=True)

if "rol" not in st.session_state:
    st.session_state.rol = None

if st.session_state.rol is None:
    st.markdown('<p class="login-header">UNIVERSIDAD ROOSEVELT - SISTEMA GTH</p>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        u = st.text_input("USUARIO")
        p = st.text_input("CONTRASEÑA", type="password")
        st.markdown('<p class="login-welcome">Bienvenido (a) al sistema de gestión de datos de los colaboradores</p>', unsafe_allow_html=True)
        if st.button("INGRESAR"):
            u_low = u.lower().strip()
            if u_low == "admin": st.session_state.rol = "Admin"
            elif u_low == "supervisor" and p == "123": st.session_state.rol = "Supervisor"
            elif u_low == "lector" and p == "123": st.session_state.rol = "Lector"
            else: st.error("Credenciales incorrectas")
            if st.session_state.rol: st.rerun()

else:
    # --- 4. SISTEMA PRINCIPAL ---
    dfs = load_data()
    es_lector = st.session_state.rol == "Lector"
    
    st.sidebar.markdown(f"<h3 style='color:yellow;'>Rol: {st.session_state.rol}</h3>", unsafe_allow_html=True)
    m = st.sidebar.radio("MENÚ", ["🔍 Consulta", "➕ Registro", "📊 Nómina General"])
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.rol = None
        st.rerun()

    if m == "🔍 Consulta":
        dni_b = st.text_input("DNI del colaborador:").strip()
        if dni_b:
            pers = dfs["PERSONAL"][dfs["PERSONAL"]["dni"] == dni_b]
            if not pers.empty:
                nom_c = pers.iloc[0]["apellidos y nombres"]
                st.markdown(f"<h2 style='color:white;'>👤 {nom_c}</h2>", unsafe_allow_html=True)
                
                h_keys = list(COLUMNAS.keys())[1:] # Saltamos "PERSONAL"
                tabs = st.tabs(h_keys)

                for i, tab in enumerate(tabs):
                    h_name = h_keys[i]
                    with tab:
                        c_df = dfs[h_name][dfs[h_name]["dni"] == dni_b] if "dni" in dfs[h_name].columns else pd.DataFrame(columns=COLUMNAS[h_name])
                        st.dataframe(c_df, use_container_width=True, hide_index=True)
                        
                        if h_name == "CONTRATOS" and not c_df.empty:
                            st.download_button("📄 Certificado Word", gen_word(nom_c, dni_b, c_df), f"Cert_{dni_b}.docx")
            else:
                st.error("Trabajador no encontrado.")

    elif m == "➕ Registro" and not es_lector:
        st.markdown("<h2 style='color:white;'>Alta de Nuevo Trabajador</h2>", unsafe_allow_html=True)
        with st.form("reg_p"):
            d = st.text_input("DNI")
            n = st.text_input("Nombres y Apellidos").upper()
            l = st.text_input("Link de Carpeta Digital")
            if st.form_submit_button("Registrar"):
                if d and n:
                    dfs["PERSONAL"] = pd.concat([dfs["PERSONAL"], pd.DataFrame([{"dni":d, "apellidos y nombres":n, "link":l}])], ignore_index=True)
                    save_data(dfs)
                    st.success("Registrado correctamente")

    elif m == "📊 Nómina General":
        st.markdown("<h2 style='color:white;'>Base de Datos General</h2>", unsafe_allow_html=True)
        st.dataframe(dfs["PERSONAL"], use_container_width=True, hide_index=True)


