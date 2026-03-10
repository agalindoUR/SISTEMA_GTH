# -*- coding: utf-8 -*-
import json
import streamlit as st
import pandas as pd
import os
from datetime import date, datetime
from io import BytesIO
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- NUEVOS IMPORTS PARA GOOGLE SHEETS ---
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import numpy as np

st.set_page_config(page_title="Gestión Roosevelt", page_icon="🎓", layout="wide")

# ==========================================
# 1. CONFIGURACIÓN Y CONSTANTES
# ==========================================
DB = "DB_SISTEMA_GTH.xlsx"
F_N = "MG. ARTURO JAVIER GALINDO MARTINEZ"
F_C = "JEFE DE GESTIÓN DEL TALENTO HUMANO"

MOTIVOS_CESE = ["Término de contrato", "Renuncia", "Despido", "Mutuo acuerdo", "Fallecimiento", "Otros"]

COLUMNAS = {
    "PERSONAL": ["id", "dni", "apellidos", "nombres", "apellidos y nombres", "sexo", "estado_civil", "sede", "link", "area"],
    "DATOS GENERALES": ["id", "dni", "apellidos y nombres", "dirección", "estado civil", "fecha de nacimiento", "edad", "telefono", "correo", "area"], 
    "DATOS FAMILIARES": ["parentesco", "apellidos y nombres", "dni", "fecha de nacimiento", "edad", "estudios", "telefono"],
    "EXP. LABORAL": ["tipo de experiencia", "lugar", "puesto", "fecha inicio", "fecha de fin", "motivo cese"],
    "FORM. ACADEMICA": ["grado, titulo o especialización", "descripcion", "universidad", "año"],
    "INVESTIGACION": ["año publicación", "autor, coautor o asesor", "tipo de investigación publicada", "nivel de publicación", "lugar de publicación"],
    # NUEVAS COLUMNAS DE CONTRATOS APLICADAS:
    "CONTRATOS": ["id", "dni", "apellidos y nombres", "cargo", "area", "remuneración básica", "bonificación", "condición de trabajo", "f_inicio", "f_fin", "tipo de trabajador", "modalidad", "temporalidad", "link", "tipo contrato", "estado", "motivo cese"],
    "VACACIONES": ["periodo", "fecha de inicio", "fecha de fin", "días generados", "días gozados", "saldo", "link"],
    "OTROS BENEFICIOS": ["periodo", "tipo de beneficio", "link"],
    "MERITOS Y DEMERITOS": ["periodo", "merito o demerito", "motivo", "link"],
    "EVALUACION DEL DESEMPEÑO": ["periodo", "merito o demerito", "motivo", "link"],
    "LIQUIDACIONES": ["periodo", "firmo", "link"]
}

# ==========================================
# 2. FUNCIONES DE DATOS Y WORD (VERSIÓN GOOGLE SHEETS)
# ==========================================

SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
SHEET_NAME = "DB_SISTEMA_GTH" # <- Asegúrate de que tu Google Sheet se llame exactamente así

def obtener_credenciales():
    if "google_json" in st.secrets:
        creds_dict = json.loads(st.secrets["google_json"])
        return ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
    else:
        return ServiceAccountCredentials.from_json_keyfile_name("credenciales.json", SCOPE)

@st.cache_data(ttl=600)
def load_data():
    creds = obtener_credenciales()
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME)

    # ⚡ SÚPER OPTIMIZACIÓN: Pedir todas las hojas en 1 sola petición
    hojas_existentes = {ws.title: ws for ws in sheet.worksheets()}

    dfs = {}
    for h, cols_requeridas in COLUMNAS.items():
        if h in hojas_existentes:
            try:
                worksheet = hojas_existentes[h]
                # 1. Obtenemos los datos crudos
                data = worksheet.get_all_records()
                df = pd.DataFrame(data)

                # 2. LIMPIEZA DE CABECERAS (Para evitar el error de duplicados y tildes)
                # Pasamos todo a minúsculas y quitamos espacios para procesar internamente
                df.columns = [str(c).strip().lower()
                              .replace('á', 'a').replace('é', 'e')
                              .replace('í', 'i').replace('ó', 'o')
                              .replace('ú', 'u') for c in df.columns]

                # 3. RENOMBRADO ESTRATÉGICO (Estandarizar AREA y otros)
                # Buscamos cualquier variante de "area" y la nombramos "area"
                for col in df.columns:
                    if "rea" in col: # detecta area, AREA, área, Área
                        df.rename(columns={col: "area"}, inplace=True)
                
                # Otros renombres específicos de tu lógica
                if h == "CONTRATOS":
                    if "sueldo" in df.columns: df.rename(columns={"sueldo": "remuneración básica"}, inplace=True)
                    if "tipo colaborador" in df.columns: df.rename(columns={"tipo colaborador": "tipo de trabajador"}, inplace=True)
                    if "tipo" in df.columns and "tipo de trabajador" not in df.columns: df.rename(columns={"tipo": "tipo de trabajador"}, inplace=True)

                # 4. LIMPIEZA DE DNI
                if "dni" in df.columns:
                    df["dni"] = df["dni"].astype(str).str.strip().str.replace(r'\.0$', '', regex=True).str.zfill(8)

                # 5. ASEGURAR COLUMNAS REQUERIDAS (Evita que la App explote si falta una columna)
                for req_col in cols_requeridas:
                    req_col_clean = req_col.strip().lower()
                    if req_col_clean not in df.columns:
                        df[req_col_clean] = "" # Creamos la columna si no existe en el Excel

                dfs[h] = df

            except Exception as e:
                st.error(f"⚠️ Error al procesar la pestaña '{h}': {e}")
                dfs[h] = pd.DataFrame() # Entregar vacío para que no rompa el resto
        else:
            dfs[h] = pd.DataFrame()
            
    return dfs

def save_data(dfs):
    creds = obtener_credenciales()
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME)

    for h, df in dfs.items():
        worksheet = sheet.worksheet(h)
        df_s = df.copy()
        
        # --- EL ESCUDO ANTI-CLONACIÓN ---
        # Si el sistema detecta columnas repetidas (como "area" o "AREA"), las borra y deja solo una
        df_s = df_s.loc[:, ~df_s.columns.duplicated()]
        
        df_s = df_s.fillna("")
        df_s = df_s.astype(str).replace("nan", "")
        df_s.columns = [c.upper() for c in df_s.columns]
        
        worksheet.clear()
        worksheet.update([df_s.columns.values.tolist()] + df_s.values.tolist())
    
    # Limpia la memoria automáticamente para que no tengas que darle F5 a cada rato
    st.cache_data.clear()

def get_consolidated_contracts(df_c):
    # Función inteligente para fusionar contratos consecutivos
    if df_c.empty: return df_c
    df_c = df_c.copy()
    df_c['f_inicio'] = pd.to_datetime(df_c['f_inicio'], errors='coerce')
    df_c['f_fin'] = pd.to_datetime(df_c['f_fin'], errors='coerce')
    df_c = df_c.sort_values('f_inicio').dropna(subset=['f_inicio'])
    
    merged = []
    for _, row in df_c.iterrows():
        if not merged:
            merged.append(row.to_dict())
        else:
            last = merged[-1]
            # Si la fecha de inicio del nuevo contrato es justo un día después del fin del anterior (o antes)
            if pd.notnull(last['f_fin']) and row['f_inicio'] <= last['f_fin'] + pd.Timedelta(days=1):
                # Ampliamos la fecha final
                last['f_fin'] = max(last['f_fin'], row['f_fin']) if pd.notnull(row['f_fin']) else row['f_fin']
                # Actualizamos al cargo más reciente
                last['cargo'] = row['cargo'] 
            else:
                merged.append(row.to_dict())
    return pd.DataFrame(merged)

def gen_word(nom, dni, df_c):
    doc = Document()
    section = doc.sections[0]
    section.page_height, section.page_width = Inches(11.69), Inches(8.27)
    section.top_margin, section.bottom_margin = Inches(1.6), Inches(1.2)

    if os.path.exists("header.png"):
        p_h = section.header.paragraphs[0]
        p_h.paragraph_format.left_indent = Inches(-1.0)
        p_h.add_run().add_picture("header.png", width=Inches(8.27))

    if os.path.exists("footer.png"):
        p_f = section.footer.paragraphs[0]
        p_f.paragraph_format.left_indent = Inches(-1.0)
        p_f.add_run().add_picture("footer.png", width=Inches(8.27))

    p_tit = doc.add_paragraph()
    p_tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_tit = p_tit.add_run("CERTIFICADO DE TRABAJO")
    r_tit.bold, r_tit.font.name, r_tit.font.size = True, 'Arial', Pt(18)

    doc.add_paragraph("\nLa oficina de Gestión de Talento Humano De La Universidad Privada De Huancayo “Franklin Roosevelt”, certifica que:").alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    p_inf = doc.add_paragraph()
    p_inf.add_run("El(la) TRABAJADOR(A) ").bold = False
    p_inf.add_run(nom).bold = True
    p_inf.add_run(f", identificado(a) con DNI N° {dni}, laboró bajo el siguiente detalle:")

    # Obtenemos los contratos fusionados automáticamente
    df_merged = get_consolidated_contracts(df_c)

    t = doc.add_table(rows=1, cols=3)
    t.style = 'Table Grid'
    for i, h in enumerate(["CARGO", "FECHA INICIO", "FECHA FIN"]):
        celda = t.rows[0].cells[i]
        celda.text = h
        celda.paragraphs[0].runs[0].font.bold = True

    for _, fila in df_merged.iterrows():
        celdas = t.add_row().cells
        celdas[0].text = str(fila.get('cargo', ''))
        celdas[1].text = pd.to_datetime(fila['f_inicio']).strftime('%d/%m/%Y') if pd.notnull(fila['f_inicio']) else ""
        celdas[2].text = pd.to_datetime(fila['f_fin']).strftime('%d/%m/%Y') if pd.notnull(fila['f_fin']) else ""

    doc.add_paragraph("\nSe expide el presente a solicitud del interesado para los fines que considere convenientes.").alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    doc.add_paragraph(f"\nHuancayo, {date.today().strftime('%d/%m/%Y')}").alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f = doc.add_paragraph()
    f.alignment = WD_ALIGN_PARAGRAPH.CENTER
    f.add_run("\n\n__________________________\n" + F_N + "\n" + F_C).bold = True

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf
# ==============================================================================
# FUNCIÓN 2: GENERAR PAPELETA DE VACACIONES INDIVIDUAL (Word Duplicado A4)
# ==============================================================================
def gen_papeleta_vac(apellidos, nombres, dni_b, position, f_ingreso, period, start_d, end_d, days):
    template_path = "Template_Papeleta.docx"
    
    if not os.path.exists(template_path):
        st.error(f"⚠️ No se encontró la plantilla en: {template_path}. Por favor crea el archivo Word.")
        return None

    doc = Document(template_path)
    
    hoy = date.today()
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    txt_firma = f"Huancayo, {hoy.day} de {meses[hoy.month-1]} de {hoy.year}"

    fin_dt = pd.to_datetime(end_d, errors='coerce')
    if pd.notnull(fin_dt):
        retorno_dt = fin_dt + pd.Timedelta(days=1)
        if retorno_dt.weekday() == 6:  # Si cae Domingo (6), pasa a Lunes
            retorno_dt += pd.Timedelta(days=1)
        str_retorno = retorno_dt.strftime("%d/%m/%Y")
    else:
        str_retorno = ""

    replacements = {
        "{{APELLIDOS}}": str(apellidos).upper(),
        "{{NOMBRES}}": str(nombres).upper(),
        "{{DNI}}": str(dni_b),
        "{{CARGO}}": str(position).upper(),
        "{{F_INGRESO}}": f_ingreso.strftime("%d/%m/%Y") if isinstance(f_ingreso, (date, datetime)) else str(f_ingreso),
        "{{PERIODO}}": str(period),
        "{{F_INICIO}}": start_d.strftime("%d/%m/%Y") if isinstance(start_d, (date, datetime)) else str(start_d),
        "{{F_FIN}}": end_d.strftime("%d/%m/%Y") if isinstance(end_d, (date, datetime)) else str(end_d),
        "{{F_RETORNO}}": str_retorno,
        "{{DIAS}}": str(days),
        "{{FECHA_FIRMA}}": txt_firma
    }

    def replace_in_element(element, reps):
        for run in element.runs:
            for key, value in reps.items():
                if key in run.text:
                    run.text = run.text.replace(key, value)

    for paragraph in doc.paragraphs:
        replace_in_element(paragraph, replacements)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    replace_in_element(paragraph, replacements)

    docx_stream = BytesIO()
    doc.save(docx_stream)
    docx_stream.seek(0)
    return docx_stream

# ==========================================
# 3. ESTILOS CSS
# ==========================================
st.markdown("""
<style>
    .stApp { background-color: #4a0000 !important; }
    [data-testid="stHeader"] { display: none !important; }
    
    .stApp p, .stMarkdown p { color: #FFFFFF; } 
    .stApp h1, .stApp h2, .stApp h3 { color: #FFD700 !important; }
    
    [data-testid="stSidebar"] { background-color: #4a0000 !important; }
    [data-testid="stSidebar"] h3 { color: #FFD700 !important; font-weight: bold !important; }
    [data-testid="stSidebar"] [data-testid="stImage"] { background-color: #FFF9C4 !important; border: 4px solid #FFD700 !important; border-radius: 15px !important; padding: 10px !important; }
    div[role="radiogroup"] label { background-color: transparent !important; }
    div[role="radiogroup"] label p { color: #FFFFFF !important; font-weight: bold !important; font-size: 16px !important; }
    
    /* ========================================= */
    /* BOTONES CON MEJOR CONTRASTE               */
    /* ========================================= */
    div.stButton > button, [data-testid="stFormSubmitButton"] > button { 
        background-color: #FFD700 !important; /* Amarillo Roosevelt */
        border: 2px solid #4a0000 !important; 
        border-radius: 10px !important; 
    }

    /* Forzamos el color Guinda en TODO el texto de CUALQUIER botón */
    div.stButton > button *, [data-testid="stFormSubmitButton"] > button *,
    div.stButton > button p, [data-testid="stFormSubmitButton"] > button p { 
        color: #4a0000 !important; 
        font-weight: bold !important; 
        font-size: 16px !important; 
    }

    div.stButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover { 
        background-color: #ffffff !important; 
        border-color: #FFD700 !important; 
    }

   /* ========================================= */
   /* FONDOS Y CAJAS DE TEXTO                   */
   /* ========================================= */
    [data-testid="stExpander"] { 
        background-color: #FFF9C4 !important; 
        border: 2px solid #FFD700 !important; 
        border-radius: 10px !important; 
    }
    
    [data-testid="stExpander"] details { background-color: transparent !important; }
    [data-testid="stExpander"] summary { background-color: #FFD700 !important; padding: 10px !important; border-radius: 8px 8px 0 0 !important; }
    [data-testid="stExpander"] summary p { color: #4a0000 !important; font-weight: bold !important; font-size: 16px !important; }

    /* Damos fondo blanco y borde a las cajas donde se escribe para que resalten sobre el crema */
    [data-baseweb="input"], [data-baseweb="select"], [data-baseweb="textarea"] { 
        background-color: #FFFFFF !important; 
        border: 1px solid #4a0000 !important; 
        border-radius: 5px !important; 
    }
    
    /* El texto que tú escribes será negro */
    .stApp input, .stApp select, .stApp textarea, [data-baseweb="select"] span { 
        color: #000000 !important; 
        font-weight: bold !important; 
        -webkit-text-fill-color: #000000 !important;
    }

    /* Fix para los mensajes de advertencia (Ej: Activa la casilla) */
    [data-testid="stAlert"] { 
        background-color: #FFF9C4 !important; 
        border: 2px solid #FFD700 !important; 
        border-radius: 10px !important;
    }
    [data-testid="stAlert"] p, [data-testid="stAlert"] span, [data-testid="stAlert"] svg { 
        color: #4a0000 !important; 
        font-weight: bold !important; 
        font-size: 16px !important; 
    }

    /* ========================================= */
    /* TABLAS INTERACTIVAS                       */
    /* ========================================= */
    [data-testid="stDataEditor"], [data-testid="stTable"], .stTable { background-color: white !important; border-radius: 10px !important; overflow: hidden !important; }
    
    [data-testid="stDataEditor"] .react-grid-HeaderCell span { 
        color: #000000 !important; 
        font-weight: 900 !important; 
        font-size: 15px !important; 
        text-transform: uppercase !important; 
    }
    
    thead tr th { background-color: #FFF9C4 !important; color: #000000 !important; font-weight: bold !important; text-transform: uppercase !important; border: 1px solid #f0f0f0 !important; }
    
    /* ========================================= */
    /* SUBTÍTULOS (LABELS DE LOS FORMULARIOS)    */
    /* ========================================= */
    
    /* 1. Subtítulos generales (Login, Buscar, Alta Trabajador) en color DORADO */
    label p, label span, .stApp label p { 
        color: #FFD700 !important; 
        font-weight: bold !important; 
        font-size: 16px !important; 
    }
    
    /* 2. Subtítulos SOLO dentro de los recuadros desplegables (fondo crema) en color GUINDA */
    [data-testid="stExpander"] label p, [data-testid="stExpander"] label span { 
        color: #4a0000 !important; 
        font-weight: bold !important; 
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 4. LÓGICA DE DATOS Y SESIÓN
# ==========================================
if "rol" not in st.session_state: st.session_state.rol = None

if st.session_state.rol is None:
    st.markdown("<h3 style='text-align: center; color: #FFD700;'>¡Tu talento es importante! :)</h3>", unsafe_allow_html=True)

    col_logo1, col_logo2, col_logo3 = st.columns([1, 1.2, 1])
    with col_logo2:
        if os.path.exists("Logo_amarillo.png"): st.image("Logo_amarillo.png", use_container_width=False)

    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        u = st.text_input("USUARIO").lower().strip()
        p = st.text_input("CONTRASEÑA", type="password")
        st.markdown('<p style="color:white; text-align:center; font-weight:bold; margin-top:15px;">Bienvenido (a) al sistema de gestión de datos de los colaboradores</p>', unsafe_allow_html=True)

        if st.button("INGRESAR"):
            if u == "admin": st.session_state.rol = "Admin"
            elif u == "supervisor" and p == "123": st.session_state.rol = "Supervisor"
            elif u == "lector" and p == "123": st.session_state.rol = "Lector"
            else: st.error("Credenciales incorrectas")

            if st.session_state.rol: st.rerun()

else:
    dfs = load_data()
    es_lector = st.session_state.rol == "Lector"

    with st.sidebar:
        st.markdown("<br>", unsafe_allow_html=True)
        col_logo_1, col_logo_2, col_logo_3 = st.columns([1, 2, 1]) 
        with col_logo_2:
            if os.path.exists("Logo_guindo.png"): st.image("Logo_guindo.png", use_container_width=False)
        st.markdown("<br>", unsafe_allow_html=True)

        # --- LÓGICA DE MENÚS INTELIGENTES ---
        if "menu_p" not in st.session_state: st.session_state.menu_p = "🔍 Consulta"
        if "menu_r" not in st.session_state: st.session_state.menu_r = None
        if "menu_activo" not in st.session_state: st.session_state.menu_activo = "🔍 Consulta"

        def click_menu_p():
            st.session_state.menu_activo = st.session_state.menu_p
            st.session_state.menu_r = None # Apaga los reportes

        def click_menu_r():
            if st.session_state.menu_r is not None:
                st.session_state.menu_activo = st.session_state.menu_r
                st.session_state.menu_p = None # Apaga el menú principal

        st.markdown("### 🛠️ MENÚ PRINCIPAL")
        st.radio("Menú Principal", ["🔍 Consulta", "➕ Registro", "📊 Nómina General"], key="menu_p", on_change=click_menu_p, label_visibility="collapsed")
        
        st.markdown("<h3 style='color: #FFD700;'>📊 REPORTES</h3>", unsafe_allow_html=True)
        # Usamos index=None para que se pueda desmarcar sin textos extraños
        st.radio("Reportes", ["Reporte General", "Cumpleañeros", "Vacaciones", "Vencimientos"], key="menu_r", on_change=click_menu_r, index=None, label_visibility="collapsed")
        
        m = st.session_state.menu_activo

        st.markdown("---")
        if st.button("🚪 Cerrar Sesión", key="btn_logout"):
            st.session_state.rol = None
            st.rerun()

  # === SECCIÓN CONSULTA ===
    if m == "🔍 Consulta":
        st.markdown("<h2 style='color: #FFD700;'>Búsqueda de Colaborador</h2>", unsafe_allow_html=True)

        df_per_consulta = dfs["PERSONAL"].copy()
        
        df_per_consulta["dni_str"] = df_per_consulta.get("dni", pd.Series([""]*len(df_per_consulta))).astype(str).str.strip()
        apellidos_col = df_per_consulta.get("apellidos", pd.Series([""]*len(df_per_consulta))).fillna("").astype(str).str.strip()
        nombres_col = df_per_consulta.get("nombres", pd.Series([""]*len(df_per_consulta))).fillna("").astype(str).str.strip()
        
        df_per_consulta["nom_str"] = (apellidos_col + " " + nombres_col).str.strip()
        df_per_consulta["search_str"] = df_per_consulta["dni_str"] + " - " + df_per_consulta["nom_str"]
        
        opciones_buscador = [""] + [x for x in df_per_consulta["search_str"].tolist() if x != " - "]

        selected_search = st.selectbox("🔍 Escriba el DNI o Apellidos y Nombres:", opciones_buscador)

        if selected_search:
            dni_buscado = selected_search.split(" - ")[0].strip()
            
            fila_pers = df_per_consulta[df_per_consulta["dni_str"] == dni_buscado]
            if not fila_pers.empty:
                nom_c = fila_pers.iloc[0]["nom_str"]
                # --- AQUÍ ESTÁ LA SOLUCIÓN ---
                ape_c = str(fila_pers.iloc[0].get("apellidos", "")).strip()
                nom_p_c = str(fila_pers.iloc[0].get("nombres", "")).strip()
                # -----------------------------

                st.markdown(f"""
                    <div style='border-bottom: 2px solid #FFD700; padding-bottom: 10px; margin-bottom: 20px; display: flex; align-items: center;'>
                        <h1 style='color: white; margin: 0; margin-right: 15px; font-size: 3em;'>👤</h1>
                        <h1 style='color: #FFD700; margin: 0; font-size: 2.5em;'>{nom_c}</h1>
                    </div>
                """, unsafe_allow_html=True)
                
                t_noms = ["Datos Generales", "Exp. Laboral", "Form. Académica", "Investigación", "Datos Familiares", "Contratos", "Vacaciones", "Otros Beneficios", "Méritos/Demer.", "Evaluación", "Liquidaciones"]
                h_keys = ["DATOS GENERALES", "EXP. LABORAL", "FORM. ACADEMICA", "INVESTIGACION", "DATOS FAMILIARES", "CONTRATOS", "VACACIONES", "OTROS BENEFICIOS", "MERITOS Y DEMERITOS", "EVALUACION DEL DESEMPEÑO", "LIQUIDACIONES"]

                tabs = st.tabs(t_noms)

                for i, tab in enumerate(tabs):
                    h_name = h_keys[i]
                    with tab:
                        if "dni" in dfs[h_name].columns:
                            c_df = dfs[h_name][dfs[h_name]["dni"] == dni_buscado]
                        else:
                            c_df = pd.DataFrame(columns=COLUMNAS.get(h_name, []))

                        if h_name == "CONTRATOS":
                            df_contratos = dfs["CONTRATOS"][dfs["CONTRATOS"]["dni"] == dni_buscado]
                            if not df_contratos.empty:
                                st.markdown("""
                                    <style>
                                    [data-testid="stDownloadButton"] button { background-color: #FFD700 !important; border: 2px solid #4A0000 !important; }
                                    [data-testid="stDownloadButton"] button p { color: #4A0000 !important; font-weight: bold !important; font-size: 16px !important; }
                                    [data-testid="stDownloadButton"] button:hover { background-color: #ffffff !important; border: 2px solid #FFD700 !important; }
                                    </style>
                                """, unsafe_allow_html=True)
                                word_file = gen_word(nom_c, dni_buscado, df_contratos)
                                st.download_button("📄 Generar Certificado de Trabajo", data=word_file, file_name=f"Certificado_{dni_buscado}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                                st.markdown("<br>", unsafe_allow_html=True)

                        if h_name == "VACACIONES":
                            df_tc = df_contratos[df_contratos["tipo contrato"].astype(str).str.lower().str.contains("planilla", na=False)] if "df_contratos" in locals() else pd.DataFrame()
                            
                            detalles = []
                            dias_generados_totales = 0
                            dias_gozados_totales = pd.to_numeric(c_df["días gozados"], errors='coerce').sum()

                            if not df_tc.empty:
                                df_tc_calc = df_tc.copy()
                                df_tc_calc['f_inicio_dt'] = pd.to_datetime(df_tc_calc['f_inicio'], errors='coerce')
                                df_tc_calc['f_fin_dt'] = pd.to_datetime(df_tc_calc['f_fin'], errors='coerce')
                                
                                start_global = df_tc_calc['f_inicio_dt'].min()
                                
                                if pd.notnull(start_global):
                                    start_global = start_global.date()
                                    curr_start = start_global
                                    
                                    while curr_start <= date.today():
                                        curr_end = (pd.to_datetime(curr_start) + pd.DateOffset(years=1) - pd.Timedelta(days=1)).date()
                                        days_in_p = 0
                                        
                                        for _, r in df_tc_calc.iterrows():
                                            c_start = r['f_inicio_dt'].date() if pd.notnull(r['f_inicio_dt']) else None
                                            c_end = r['f_fin_dt'].date() if pd.notnull(r['f_fin_dt']) else None
                                            if c_start and c_end:
                                                o_start = max(curr_start, c_start)
                                                o_end = min(curr_end, c_end, date.today())
                                                if o_start <= o_end: 
                                                    days_in_p += (o_end - o_start).days + 1
                                                
                                        # --- SOLUCIÓN: CÁLCULO PROPORCIONAL EXACTO ---
                                        # Obtenemos los días totales reales que tiene ese periodo (365 o 366 si cruza un bisiesto)
                                        total_dias_periodo = (curr_end - curr_start).days + 1
                                        
                                        # Nueva fórmula: garantizamos un máximo exacto de 30 días por año completo
                                        gen_p = round((days_in_p / total_dias_periodo) * 30, 2)
                                        # ---------------------------------------------
                                        
                                        p_name = f"{curr_start.year}-{curr_start.year+1}"
                                        
                                        goz_df = c_df[c_df["periodo"].astype(str).str.strip() == p_name]
                                        goz_p = pd.to_numeric(goz_df["días gozados"], errors='coerce').sum()
                                        
                                        if gen_p > 0 or goz_p > 0:
                                            detalles.append({"Periodo": p_name, "Del": curr_start.strftime("%d/%m/%Y"), "Al": curr_end.strftime("%d/%m/%Y"), "Días Generados": gen_p, "Días Gozados": goz_p, "Saldo": round(gen_p - goz_p, 2)})
                                        
                                        dias_generados_totales += gen_p
                                        curr_start = (pd.to_datetime(curr_start) + pd.DateOffset(years=1)).date()

                            saldo_v = round(dias_generados_totales - dias_gozados_totales, 2)

                            st.markdown(f"""
                            <div style="display: flex; gap: 15px; margin-bottom: 20px;">
                                <div style="flex: 1; background-color: #4A0000; padding: 20px; border-radius: 10px; text-align: center; border: 2px solid #FFD700;"><h2 style="color: #FFD700; margin: 0; font-size: 2.5em;">{dias_generados_totales:.2f}</h2><p style="color: #FFFFFF; margin: 0; font-weight: bold; font-size: 1.1em;">Días Generados Totales</p></div>
                                <div style="flex: 1; background-color: #4A0000; padding: 20px; border-radius: 10px; text-align: center; border: 2px solid #FFD700;"><h2 style="color: #FFD700; margin: 0; font-size: 2.5em;">{dias_gozados_totales:.2f}</h2><p style="color: #FFFFFF; margin: 0; font-weight: bold; font-size: 1.1em;">Días Gozados</p></div>
                                <div style="flex: 1; background-color: #4A0000; padding: 20px; border-radius: 10px; text-align: center; border: 2px solid #FFD700;"><h2 style="color: #FFD700; margin: 0; font-size: 2.5em;">{saldo_v:.2f}</h2><p style="color: #FFFFFF; margin: 0; font-weight: bold; font-size: 1.1em;">Saldo Disponible</p></div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if detalles:
                                st.markdown("<h4 style='color: #FFD700;'>Desglose por Periodos</h4>", unsafe_allow_html=True)
                                div_table = "<div style='display: flex; flex-direction: column; width: 100%; border: 2px solid #FFD700; border-radius: 8px; overflow: hidden; margin-bottom: 20px;'><div style='display: flex; background-color: #4A0000; color: #FFD700; font-weight: bold;'><div style='flex: 1; padding: 12px; text-align: center; border-right: 1px solid #FFD700;'>PERIODO</div><div style='flex: 1; padding: 12px; text-align: center; border-right: 1px solid #FFD700;'>DEL</div><div style='flex: 1; padding: 12px; text-align: center; border-right: 1px solid #FFD700;'>AL</div><div style='flex: 1; padding: 12px; text-align: center; border-right: 1px solid #FFD700;'>DÍAS GENERADOS</div><div style='flex: 1; padding: 12px; text-align: center; border-right: 1px solid #FFD700;'>DÍAS GOZADOS</div><div style='flex: 1; padding: 12px; text-align: center;'>SALDO</div></div>"
                                for d in detalles:
                                    div_table += f"<div style='display: flex; background-color: #FFF9C4; color: #4A0000; font-weight: bold; border-top: 1px solid #FFD700;'><div style='flex: 1; padding: 10px; text-align: center; border-right: 1px solid #FFD700;'>{d['Periodo']}</div><div style='flex: 1; padding: 10px; text-align: center; border-right: 1px solid #FFD700;'>{d['Del']}</div><div style='flex: 1; padding: 10px; text-align: center; border-right: 1px solid #FFD700;'>{d['Al']}</div><div style='flex: 1; padding: 10px; text-align: center; border-right: 1px solid #FFD700;'>{d['Días Generados']:.2f}</div><div style='flex: 1; padding: 10px; text-align: center; border-right: 1px solid #FFD700;'>{d['Días Gozados']:.2f}</div><div style='flex: 1; padding: 10px; text-align: center;'>{d['Saldo']:.2f}</div></div>"
                                div_table += "</div>"
                                st.markdown(div_table, unsafe_allow_html=True)

                        vst = c_df.copy()
                        
                        cols_ocultar = [c for c in vst.columns if c.lower() in ["apellidos y nombres", "apellidos", "nombres"]]
                        vst = vst.drop(columns=cols_ocultar)

                        col_conf = {}
                        for col in vst.columns:
                            if "fecha" in col.lower() or "f_" in col.lower():
                                vst[col] = pd.to_datetime(vst[col], errors='coerce').dt.date
                                col_conf[str(col).upper()] = st.column_config.DateColumn(format="DD/MM/YYYY")

                        vst.columns = [str(col).upper() for col in vst.columns]
                        # --- SOLUCIÓN AL ERROR ---
                        # Si hay columnas duplicadas en Google Sheets, esto las elimina para que la app no colapse
                        vst = vst.loc[:, ~vst.columns.duplicated()]
        
                        if "SEL" not in vst.columns:
                            vst.insert(0, "SEL", False)
                        
                        # --- MAGIA: OCULTAR Y ORDENAR COLUMNAS ---
                        # 1. Lista de todo lo que queremos desaparecer de la vista
                        columnas_basura = ["DNI", "FECHA DE INICIO", "FECHA DE FIN", "DÍAS GENERADOS", "DIAS GENERADOS", "SALDO"]
                        for col in columnas_basura:
                            if col in vst.columns:
                                col_conf[col] = None
                                
                        # 2. Reordenar las columnas para que F_INICIO y F_FIN salgan primero
                        cols_importantes = ["SEL", "PERIODO", "F_INICIO", "F_FIN", "DÍAS GOZADOS", "DIAS GOZADOS"]
                        cols_finales = [c for c in cols_importantes if c in vst.columns] + [c for c in vst.columns if c not in cols_importantes]
                        vst = vst[cols_finales]
                        # ----------------------------------------

                        st.markdown("""<style>[data-testid="stDataEditor"] { border: 2px solid #FFD700 !important; border-radius: 10px !important; }</style>""", unsafe_allow_html=True)
                        # ... (aquí va tu st.data_editor)
                        ed = st.data_editor(vst, hide_index=True, use_container_width=False, column_config=col_conf, key=f"ed_{h_name}")
                        
                       # 1. Detectar si hay una fila seleccionada
                        sel = ed[ed["SEL"] == True]

                        if not sel.empty and not es_lector:
                            idx = sel.index[0]
                            fila = sel.iloc[0]
                            st.markdown("### 📝 Editar / Eliminar Registro")
                            
                            # CLAVE: El formulario envuelve TODO, incluyendo los botones
                            with st.form(key=f"f_ed_{h_name}_{idx}"):
                                if h_name == "CONTRATOS":
                                    st.markdown("### 📝 Editar / Eliminar Contrato")
                                    c1, c2 = st.columns(2)
                                    
                                    with c1:
                                        n_car = st.text_input("Cargo", value=str(fila.get("cargo", "")))
                                        n_area_cont = st.text_input("Área", value=str(fila.get("area", ""))).upper()
                                        
                                        # CORRECCIÓN: Quitamos tilde en "remuneracion basica"
                                        try: val_rem = float(fila.get("remuneracion basica", 0.0))
                                        except: val_rem = 0.0
                                        n_rem = st.number_input("Remuneración básica", value=val_rem)
                                        
                                        # CORRECCIÓN: Quitamos tildes en "bonificacion" y "condicion de trabajo"
                                        n_bon = st.text_input("Bonificación", value=str(fila.get("bonificacion", "")))
                                        n_cond = st.text_input("Condición de trabajo", value=str(fila.get("condicion de trabajo", "")))
                                        
                                        try: ini_val = pd.to_datetime(fila.get("f_inicio")).date()
                                        except: ini_val = date.today()
                                        n_ini = st.date_input("Inicio", value=ini_val, format="DD/MM/YYYY")
                                        
                                        try: fin_val = pd.to_datetime(fila.get("f_fin")).date()
                                        except: fin_val = date.today()
                                        n_fin = st.date_input("Fin", value=fin_val, format="DD/MM/YYYY")

                                    with c2:
                                        v_ttrab = str(fila.get("tipo de trabajador", "Administrativo"))
                                        opts_tt = ["Administrativo", "Docente", "Externo"]
                                        if v_ttrab not in opts_tt and v_ttrab: opts_tt.append(v_ttrab)
                                        n_ttrab = st.selectbox("Tipo de trabajador", opts_tt, index=opts_tt.index(v_ttrab) if v_ttrab in opts_tt else 0)
                                        
                                        v_mod = str(fila.get("modalidad", "Presencial"))
                                        opts_mod = ["Presencial", "Semipresencial", "Virtual"]
                                        if v_mod not in opts_mod and v_mod: opts_mod.append(v_mod)
                                        n_mod = st.selectbox("Modalidad", opts_mod, index=opts_mod.index(v_mod) if v_mod in opts_mod else 0)
                                        
                                        v_tem = str(fila.get("temporalidad", "Plazo fijo"))
                                        opts_tem = ["Plazo fijo", "Plazo indeterminado", "Ordinarizado"]
                                        if v_tem not in opts_tem and v_tem: opts_tem.append(v_tem)
                                        n_tem = st.selectbox("Temporalidad", opts_tem, index=opts_tem.index(v_tem) if v_tem in opts_tem else 0)
                                        
                                        n_lnk = st.text_input("Link", value=str(fila.get("link", "")))
                                        
                                        v_tcont = str(fila.get("tipo contrato", "Planilla completo"))
                                        opts_tcon = ["Planilla completo", "Tiempo Parcial", "Recibo por Honorarios", "Otro"]
                                        if v_tcont not in opts_tcon and v_tcont: opts_tcon.append(v_tcont)
                                        n_tcont = st.selectbox("Tipo Contrato", opts_tcon, index=opts_tcon.index(v_tcont) if v_tcont in opts_tcon else 0)

                                        est_e = "ACTIVO" if n_fin >= date.today() else "CESADO"
                                        
                                        v_mot = str(fila.get("motivo cese", "Vigente"))
                                        opts_mot = ["Vigente"] + MOTIVOS_CESE
                                        if v_mot not in opts_mot and v_mot: opts_mot.append(v_mot)
                                        mot_e = st.selectbox("Motivo Cese", opts_mot, index=opts_mot.index(v_mot) if v_mot in opts_mot else 0) if est_e == "CESADO" else "Vigente"

                                    st.markdown("---")
                                    b1, b2 = st.columns(2)
                                    with b1:
                                        if st.form_submit_button("💾 Actualizar Contrato", use_container_width=True):
                                            # CORRECCIÓN: El diccionario update_vals ya no tiene tildes en sus llaves
                                            update_vals = {
                                                "cargo": n_car, 
                                                "area": n_area_cont, 
                                                "remuneracion basica": n_rem, 
                                                "bonificacion": n_bon,
                                                "condicion de trabajo": n_cond, 
                                                "f_inicio": n_ini,
                                                "f_fin": n_fin, 
                                                "tipo de trabajador": n_ttrab,
                                                "modalidad": n_mod, 
                                                "temporalidad": n_tem, 
                                                "link": n_lnk, 
                                                "tipo contrato": n_tcont,
                                                "estado": est_e, 
                                                "motivo cese": mot_e
                                            }
                                            for k, v in update_vals.items():
                                                dfs[h_name].at[idx, k] = v
                                            save_data(dfs)
                                            st.success("✅ Contrato actualizado")
                                            st.rerun()
                                    with b2:
                                        if st.form_submit_button("🗑️ Eliminar Contrato", type="primary", use_container_width=True):
                                            dfs[h_name] = dfs[h_name].drop(idx)
                                            save_data(dfs)
                                            st.warning("🗑️ Contrato eliminado")
                                            st.rerun()
                        # ==========================================
                        # BOTÓN DE IMPRESIÓN DE PAPELETA (SOLO EN VACACIONES)
                        # ==========================================
                        if h_name == "VACACIONES" and not sel.empty:
                            st.markdown("---")
                            # Necesitamos el cargo actual y fecha de ingreso del trabajador
                            current_cargo = "TRABAJADOR" # Default
                            f_ingreso_val = ""
                            df_c_data = dfs["CONTRATOS"][dfs["CONTRATOS"]["dni"] == dni_buscado]
                            
                            if not df_c_data.empty:
                                try:
                                    # Obtener cargo (último contrato)
                                    last_contract = df_c_data.assign(f_fin_dt=pd.to_datetime(df_c_data['f_fin'], errors='coerce')).sort_values('f_fin_dt').iloc[-1]
                                    current_cargo = last_contract.get("cargo", "TRABAJADOR")
                                    
                                    # Obtener fecha de ingreso (primer contrato de planilla)
                                    df_planilla = df_c_data[df_c_data["tipo contrato"].astype(str).str.lower().str.contains("planilla", na=False)]
                                    if not df_planilla.empty:
                                        f_min = pd.to_datetime(df_planilla['f_inicio'], errors='coerce').min()
                                        if pd.notnull(f_min): f_ingreso_val = f_min.date()
                                except: pass

                            # Capturar datos de la fila seleccionada
                            r_sel = sel.iloc[0]
                            p_papeleta = str(r_sel.get("PERIODO", ""))
                            fi_papeleta = r_sel.get("F_INICIO")
                            ff_papeleta = r_sel.get("F_FIN")
                            dg_papeleta = r_sel.get("DÍAS GOZADOS", 0)

                            if hasattr(fi_papeleta, 'date'): fi_papeleta = fi_papeleta.date()
                            if hasattr(ff_papeleta, 'date'): ff_papeleta = ff_papeleta.date()

                            if st.button(f"📄 Generar Papeleta de Impresión (Periodo {p_papeleta})", key="btn_print_vaca_tab", use_container_width=False):
                                if pd.isnull(fi_papeleta) or pd.isnull(ff_papeleta):
                                    st.error("⚠️ La fila seleccionada no tiene fechas válidas de inicio o fin.")
                                else:
                                    # AQUÍ LLAMAMOS A LA FUNCIÓN CON TODOS LOS DATOS
                                    papeleta_word = gen_papeleta_vac(ape_c, nom_p_c, dni_buscado, current_cargo, f_ingreso_val, p_papeleta, fi_papeleta, ff_papeleta, dg_papeleta)
                                    if papeleta_word:
                                        st.markdown("""<style>[data-testid="stDownloadButton"] button { background-color: #FFD700 !important; color: #4A0000 !important; font-weight: bold !important; border: 2px solid #4A0000 !important; width: 100% !important; }</style>""", unsafe_allow_html=True)
                                        st.download_button(
                                            label=f"⬇️ Descargar Papeleta Duplicada - {nom_c}.docx",
                                            data=papeleta_word,
                                            file_name=f"Papeleta_{dni_buscado}_{p_papeleta}.docx",
                                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                            key="dl_papeleta_tab"
                                        )
                            st.markdown("---")
                        
                        if not es_lector:
                            col_a, col_b = st.columns(2)
                            cols_reales = [c for c in dfs[h_name].columns if c.lower() not in ["id", "dni", "apellidos y nombres", "apellidos", "nombres"]]

                            with col_a:
                                df_filtro = dfs[h_name][dfs[h_name]["dni"] == dni_buscado] if not dfs[h_name].empty else pd.DataFrame()
                                if h_name == "DATOS GENERALES" and len(df_filtro) > 0:
                                    st.info("📌 Los datos generales ya están registrados. Selecciona el registro en la tabla de arriba para editarlos.")
                                else:
                                   with st.expander("➕ Nuevo Registro"):
                                        
                                        # ==========================================
                                        # NUEVO REGISTRO REACTIVO DE VACACIONES
                                        # ==========================================
                                        if h_name == "VACACIONES":
                                            st.markdown("<div style='font-size: 1.5em; font-weight: bold; color: white; background-color: #4A0000; padding: 10px; border-radius: 8px; margin-bottom: 15px;'>➕ Registrar Nuevas Vacaciones</div>", unsafe_allow_html=True)
                                            
                                            if detalles:
                                                opciones_periodo = [d["Periodo"] for d in detalles]
                                                dict_generados = {d["Periodo"]: d["Días Generados"] for d in detalles}
                                                dict_saldo_actual = {d["Periodo"]: d["Saldo"] for d in detalles}
                                            else:
                                                opciones_periodo = ["Sin periodo calculado"]
                                                dict_generados = {"Sin periodo calculado": 0}
                                                dict_saldo_actual = {"Sin periodo calculado": 0}

                                            sel_periodo = st.selectbox("Periodo Vacacional", options=opciones_periodo)
                                            
                                            col_f1, col_f2 = st.columns(2)
                                            with col_f1:
                                                f_ini_val = st.date_input("Fecha de Salida (Inicio)")
                                            with col_f2:
                                                f_fin_val = st.date_input("Fecha de Retorno (Último día)")

                                            dias_gozar_calc = 0
                                            if f_fin_val >= f_ini_val:
                                                dias_gozar_calc = (f_fin_val - f_ini_val).days + 1
                                            
                                            gen_periodo = dict_generados.get(sel_periodo, 0)
                                            saldo_previo = dict_saldo_actual.get(sel_periodo, 0)
                                            nuevo_saldo = saldo_previo - dias_gozar_calc

                                            # Lógica de colores para el saldo
                                            if nuevo_saldo < 0:
                                                txt_saldo = f":red[{nuevo_saldo:.2f} (¡Saldo Negativo!)]"
                                            elif nuevo_saldo == 0:
                                                txt_saldo = f"{nuevo_saldo:.2f}"
                                            else:
                                                txt_saldo = f":green[{nuevo_saldo:.2f}]"

                                            st.info(f"""
                                            📊 **Resumen del Cálculo:**
                                            * **Días Generados (Periodo {sel_periodo}):** {gen_periodo:.2f}
                                            * **Días a Gozar (Calculado):** {dias_gozar_calc}
                                            * **Saldo Restante:** {txt_saldo}
                                            """)

                                            if st.button("💾 Guardar Registro de Vacaciones", type="primary", use_container_width=False):
                                                if dias_gozar_calc <= 0:
                                                    st.error("⚠️ La Fecha de Fin debe ser igual o posterior a la Fecha de Inicio.")
                                                else:
                                                    new_row = {"dni": dni_buscado, "periodo": sel_periodo, "f_inicio": f_ini_val, "f_fin": f_fin_val, "días gozados": dias_gozar_calc}
                                                    if not dfs[h_name].empty and "id" in dfs[h_name].columns: new_row["id"] = dfs[h_name]["id"].max() + 1
                                                    elif "id" in dfs[h_name].columns: new_row["id"] = 1
                                                    dfs[h_name] = pd.concat([dfs[h_name], pd.DataFrame([new_row])], ignore_index=True)
                                                    save_data(dfs)
                                                    st.session_state['just_saved_vacation'] = new_row
                                                    st.success("✅ Registro guardado correctamente.")
                                                    st.rerun()

                                        # ==========================================
                                        # FORMULARIOS NORMALES PARA EL RESTO DE HOJAS
                                        # ==========================================
                                        else:
                                            es_renovacion = False
                                            if h_name == "CONTRATOS" and not df_contratos.empty:
                                                es_renovacion = st.checkbox("🔄 Es Renovación (Copiar datos del último contrato)")
                                                
                                            with st.form(f"f_add_{h_name}", clear_on_submit=True):
                                                if h_name == "CONTRATOS":
                                                    d_car = ""
                                                    d_rem = 0.0
                                                    d_bon = ""
                                                    d_cond = ""
                                                    d_ini = date.today()
                                                    d_fin = date.today()
                                                    d_ttrab = "Administrativo"
                                                    d_mod = "Presencial"
                                                    d_temp = "Plazo fijo"
                                                    d_tcont = "Planilla completo"
                                                    
                                                    if es_renovacion and not df_contratos.empty:
                                                        last_c = df_contratos.assign(f_fin_dt=pd.to_datetime(df_contratos['f_fin'], errors='coerce')).sort_values('f_fin_dt').iloc[-1]
                                                        d_car = str(last_c.get("cargo", ""))
                                                        try: 
                                                            d_rem = float(last_c.get("remuneración básica", 0.0))
                                                        except: 
                                                            pass
                                                        d_bon = str(last_c.get("bonificación", ""))
                                                        d_cond = str(last_c.get("condición de trabajo", ""))
                                                        try: 
                                                            d_ini = pd.to_datetime(last_c["f_fin"]).date() + pd.Timedelta(days=1)
                                                        except: 
                                                            pass
                                                        
                                                        v_tt = str(last_c.get("tipo de trabajador", ""))
                                                        if v_tt in ["Administrativo", "Docente", "Externo"]: 
                                                            d_ttrab = v_tt
                                                            
                                                        v_m = str(last_c.get("modalidad", ""))
                                                        if v_m in ["Presencial", "Semipresencial", "Virtual"]: 
                                                            d_mod = v_m
                                                            
                                                        v_te = str(last_c.get("temporalidad", ""))
                                                        if v_te in ["Plazo fijo", "Plazo indeterminado", "Ordinarizado"]: 
                                                            d_temp = v_te
                                                            
                                                        v_tc = str(last_c.get("tipo contrato", ""))
                                                        if v_tc in ["Planilla completo", "Tiempo Parcial", "Recibo por Honorarios", "Otro"]: 
                                                            d_tcont = v_tc

                                                    car = st.text_input("Cargo", value=d_car)
                                                    rem_b = st.number_input("Remuneración básica", value=d_rem)
                                                    bono = st.text_input("Bonificación", value=d_bon)
                                                    cond = st.text_input("Condición de trabajo", value=d_cond)
                                                    ini = st.date_input("Inicio", value=d_ini, format="DD/MM/YYYY")
                                                    fin = st.date_input("Fin", value=d_fin, format="DD/MM/YYYY")
                                                    t_trab = st.selectbox("Tipo de trabajador", ["Administrativo", "Docente", "Externo"], index=["Administrativo", "Docente", "Externo"].index(d_ttrab))
                                                    mod = st.selectbox("Modalidad", ["Presencial", "Semipresencial", "Virtual"], index=["Presencial", "Semipresencial", "Virtual"].index(d_mod))
                                                    temp = st.selectbox("Temporalidad", ["Plazo fijo", "Plazo indeterminado", "Ordinarizado"], index=["Plazo fijo", "Plazo indeterminado", "Ordinarizado"].index(d_temp))
                                                    lnk = st.text_input("Link")
                                                    tcont = st.selectbox("Tipo Contrato", ["Planilla completo", "Tiempo Parcial", "Recibo por Honorarios", "Otro"], index=["Planilla completo", "Tiempo Parcial", "Recibo por Honorarios", "Otro"].index(d_tcont))
                                                    
                                                    est_a = "ACTIVO" if fin >= date.today() else "CESADO"
                                                    mot_a = st.selectbox("Motivo Cese", ["Vigente"] + MOTIVOS_CESE) if est_a == "CESADO" else "Vigente"

                                                    if st.form_submit_button("Guardar Contrato"):
                                                        nid = dfs[h_name]["id"].max() + 1 if not dfs[h_name].empty else 1
                                                        new = {"id": nid, "dni": dni_buscado, "apellidos y nombres": nom_c, "cargo": car, "remuneración básica": rem_b, "bonificación": bono, "condición de trabajo": cond, "f_inicio": ini, "f_fin": fin, "tipo de trabajador": t_trab, "modalidad": mod, "temporalidad": temp, "link": lnk, "tipo contrato": tcont, "estado": est_a, "motivo cese": mot_a}
                                                        dfs[h_name] = pd.concat([dfs[h_name], pd.DataFrame([new])], ignore_index=True)
                                                        save_data(dfs)
                                                        st.rerun()
                                                elif h_name != "VACACIONES":
                                                    new_row = {"dni": dni_buscado, "apellidos y nombres": nom_c} 
                                                    for col in cols_reales:
                                                        if "fecha" in col.lower() or "f_" in col.lower(): 
                                                            new_row[col] = st.date_input(col.title(), min_value=date(1930, 1, 1), max_value=date.today(), format="DD/MM/YYYY")
                                                        elif col.lower() == "edad":
                                                            fnac = new_row.get("fecha de nacimiento")
                                                            if fnac: 
                                                                new_row[col] = st.number_input("Edad (Calculada)", value=int(date.today().year - fnac.year - ((date.today().month, date.today().day) < (fnac.month, fnac.day))), disabled=True)
                                                            else: 
                                                                new_row[col] = st.number_input(col.title(), value=0, disabled=True)
                                                        elif col.lower() in ["remuneración", "bonificación", "sueldo", "días generados", "días gozados", "saldo", "monto"]: 
                                                            new_row[col] = st.number_input(col.title(), 0.0)
                                                        else: 
                                                            new_row[col] = st.text_input(col.title())

                                                    if st.form_submit_button("Guardar Registro"):
                                                        if not dfs[h_name].empty and "id" in dfs[h_name].columns: 
                                                            new_row["id"] = dfs[h_name]["id"].max() + 1
                                                        elif "id" in dfs[h_name].columns: 
                                                            new_row["id"] = 1
                                                        dfs[h_name] = pd.concat([dfs[h_name], pd.DataFrame([new_row])], ignore_index=True)
                                                        save_data(dfs)
                                                        st.rerun()

                            with col_b:
                                with st.expander("📝 Editar / Eliminar"):
                                    if not sel.empty:
                                        idx = sel.index[0]
                                        with st.form(f"f_edit_{h_name}"):
                                            if h_name == "CONTRATOS":
                                                n_car = st.text_input("Cargo", value=str(sel.iloc[0].get("CARGO", "")))
                                                área = st.text_input("AREA")
                                                try: 
                                                    val_rem = float(sel.iloc[0].get("REMUNERACIÓN BÁSICA", 0.0))
                                                except: 
                                                    val_rem = 0.0
                                                n_rem = st.number_input("Remuneración básica", value=val_rem)
                                                n_bon = st.text_input("Bonificación", value=str(sel.iloc[0].get("BONIFICACIÓN", "")))
                                                n_cond = st.text_input("Condición de trabajo", value=str(sel.iloc[0].get("CONDICIÓN DE TRABAJO", "")))
                                                try: 
                                                    ini_val = pd.to_datetime(sel.iloc[0].get("F_INICIO")).date()
                                                except: 
                                                    ini_val = date.today()
                                                n_ini = st.date_input("Inicio", value=ini_val, format="DD/MM/YYYY")
                                                try: 
                                                    fin_val = pd.to_datetime(sel.iloc[0].get("F_FIN")).date()
                                                except: 
                                                    fin_val = date.today()
                                                n_fin = st.date_input("Fin", value=fin_val, format="DD/MM/YYYY")
                                                
                                                v_ttrab = str(sel.iloc[0].get("TIPO DE TRABAJADOR", "Administrativo"))
                                                opts_tt = ["Administrativo", "Docente", "Externo"]
                                                if v_ttrab not in opts_tt: 
                                                    opts_tt.append(v_ttrab)
                                                n_ttrab = st.selectbox("Tipo de trabajador", opts_tt, index=opts_tt.index(v_ttrab))
                                                
                                                v_mod = str(sel.iloc[0].get("MODALIDAD", "Presencial"))
                                                opts_mod = ["Presencial", "Semipresencial", "Virtual"]
                                                if v_mod not in opts_mod: 
                                                    opts_mod.append(v_mod)
                                                n_mod = st.selectbox("Modalidad", opts_mod, index=opts_mod.index(v_mod))
                                                
                                                v_tem = str(sel.iloc[0].get("TEMPORALIDAD", "Plazo fijo"))
                                                opts_tem = ["Plazo fijo", "Plazo indeterminado", "Ordinarizado"]
                                                if v_tem not in opts_tem: 
                                                    opts_tem.append(v_tem)
                                                n_tem = st.selectbox("Temporalidad", opts_tem, index=opts_tem.index(v_tem))
                                                
                                                n_lnk = st.text_input("Link", value=str(sel.iloc[0].get("LINK", "")))
                                                
                                                v_tcont = str(sel.iloc[0].get("TIPO CONTRATO", "Planilla completo"))
                                                opts_tcon = ["Planilla completo", "Tiempo Parcial", "Recibo por Honorarios", "Otro"]
                                                if v_tcont not in opts_tcon: 
                                                    opts_tcon.append(v_tcont)
                                                n_tcont = st.selectbox("Tipo Contrato", opts_tcon, index=opts_tcon.index(v_tcont))

                                                est_e = "ACTIVO" if n_fin >= date.today() else "CESADO"
                                                v_mot = str(sel.iloc[0].get("MOTIVO CESE", "Vigente"))
                                                opts_mot = ["Vigente"] + MOTIVOS_CESE
                                                if v_mot not in opts_mot: 
                                                    opts_mot.append(v_mot)
                                                mot_e = st.selectbox("Motivo Cese", opts_mot, index=opts_mot.index(v_mot)) if est_e == "CESADO" else "Vigente"

                                                if st.form_submit_button("Actualizar"):
                                                    update_vals = {"cargo": n_car, "area": AREA,"remuneración básica": n_rem, "bonificación": n_bon, "condición de trabajo": n_cond, "f_inicio": n_ini, "f_fin": n_fin, "tipo de trabajador": n_ttrab, "modalidad": n_mod, "temporalidad": n_tem, "link": n_lnk, "tipo contrato": n_tcont, "estado": est_e, "motivo cese": mot_e}
                                                    for k, v in update_vals.items(): 
                                                        dfs[h_name].at[idx, k] = v
                                                    save_data(dfs)
                                                    st.rerun()
                                            else:
                                                edit_row = {}
                                                for col in cols_reales:
                                                    val = sel.iloc[0].get(col.upper(), "")
                                                    if "fecha" in col.lower() or "f_" in col.lower():
                                                        edit_row[col] = st.date_input(col.title(), value=pd.to_datetime(val, errors='coerce').date() if pd.notnull(pd.to_datetime(val, errors='coerce')) else date.today(), min_value=date(1930, 1, 1), max_value=date(2100, 12, 31), format="DD/MM/YYYY")
                                                    elif col.lower() == "edad":
                                                        fnac = edit_row.get("fecha de nacimiento")
                                                        if fnac: 
                                                            edit_row[col] = st.number_input("Edad (Calculada)", value=int(date.today().year - fnac.year - ((date.today().month, date.today().day) < (fnac.month, fnac.day))), disabled=True)
                                                        else: 
                                                            edit_row[col] = st.number_input(col.title(), value=int(val) if pd.notnull(val) and str(val).isdigit() else 0, disabled=True)
                                                    elif col.lower() in ["remuneración", "bonificación", "sueldo", "días generados", "días gozados", "saldo", "monto"]:
                                                        try: 
                                                            num_val = float(val) if pd.notnull(val) else 0.0
                                                        except: 
                                                            num_val = 0.0
                                                        edit_row[col] = st.number_input(col.title(), value=num_val)
                                                    else:
                                                        edit_row[col] = st.text_input(col.title(), value=str(val) if pd.notnull(val) else "")

                                                col_btn1, col_btn2 = st.columns(2)
                                                with col_btn1:
                                                    if st.form_submit_button("Actualizar Registro"):
                                                        for k, v in edit_row.items(): 
                                                            dfs[h_name].at[idx, k] = v
                                                        save_data(dfs)
                                                        st.rerun()
                                                with col_btn2:
                                                    if st.form_submit_button("🗑️ Eliminar Registro", type="primary"):
                                                        dfs[h_name] = dfs[h_name].drop(idx)
                                                        save_data(dfs)
                                                        st.rerun()
                                    else:
                                        st.info("Activa la casilla (SEL) en la tabla superior para editar o eliminar el registro.")
            else:
                st.error("DNI no encontrado en la base de datos.")
    # --- SECCIÓN REGISTRO Y NÓMINA ---
    elif m == "➕ Registro" and not es_lector:
        with st.form("reg_p", clear_on_submit=True):
            st.write("### Alta de Nuevo Trabajador")
            c1, c2 = st.columns(2)
            with c1:
                d_dni = st.text_input("DNI").strip()
                ape_form = st.text_input("Apellidos").upper().strip()
                nom_form = st.text_input("Nombres").upper().strip()
                sexo_form = st.selectbox("Sexo", ["Masculino", "Femenino"])
            with c2:
                estado_form = st.selectbox("Estado Civil", ["Soltero(a)", "Casado(a)", "Divorciado(a)", "Conviviente", "Viudo(a)", "Otro"])
                sede_form = st.selectbox("Sede de Trabajo", ["Local Giraldez", "Local San Carlos", "Local Abancay", "Local Lince", "Local Pueblo Libre"])
                area_form = st.text_input("ÁREA").upper().strip()
                link_form = st.text_input("Link File").strip()

            nom_comp = f"{ape_form}, {nom_form}" if ape_form and nom_form else ""

            if st.form_submit_button("Registrar"):
                if d_dni and ape_form and nom_form:
                    # Guardar en PERSONAL
                    nid_p = dfs["PERSONAL"]["id"].max() + 1 if not dfs["PERSONAL"].empty else 1
                    nuevo_p = {"id": nid_p, "dni": d_dni, "apellidos": ape_form, "nombres": nom_form, "apellidos y nombres": nom_comp, "sexo": sexo_form, "estado_civil": estado_form, "sede": sede_form, "link": link_form, "area": area_form}
                    dfs["PERSONAL"] = pd.concat([dfs["PERSONAL"], pd.DataFrame([nuevo_p])], ignore_index=True)
                    
                    # Guardar en DATOS GENERALES
                    nid_dg = dfs["DATOS GENERALES"]["id"].max() + 1 if not dfs["DATOS GENERALES"].empty else 1
                    nuevo_dg = {"id": nid_dg, "dni": d_dni, "apellidos y nombres": nom_comp, "area": area_form}
                    dfs["DATOS GENERALES"] = pd.concat([dfs["DATOS GENERALES"], pd.DataFrame([nuevo_dg])], ignore_index=True)
                    
                    save_data(dfs)
                    st.success("✅ Registrado con éxito")
                    st.rerun()
                else: st.error("⚠️ Complete DNI, Apellidos y Nombres.")

    elif m == "📊 Nómina General":
        st.markdown("<h2 style='color: #FFD700;'>👥 Trabajadores registrados en el sistema</h2>", unsafe_allow_html=True)
        busqueda_nom = st.text_input("🔍 Buscar por apellidos, nombres o DNI (Nómina):").strip().lower()
        df_nom = dfs["PERSONAL"].copy()
        if busqueda_nom: 
            mask_ape = df_nom['apellidos'].fillna("").str.lower().str.contains(busqueda_nom, na=False)
            mask_nom = df_nom['nombres'].fillna("").str.lower().str.contains(busqueda_nom, na=False)
            mask_dni = df_nom['dni'].astype(str).str.contains(busqueda_nom, na=False)
            df_nom = df_nom[mask_ape | mask_nom | mask_dni]
        df_ver = df_nom.copy()
        
        # CORRECCIÓN NÓMINA GENERAL: Eliminar columna redundantemente
        df_ver = df_ver.drop(columns=["apellidos y nombres"], errors='ignore')
        
        df_ver.columns = [col.upper() for col in df_ver.columns]
        df_ver.insert(0, "SEL", False)
        ed_nom = st.data_editor(df_ver, hide_index=True, use_container_width=False, key="nomina_v3_blanco")
        filas_sel = ed_nom[ed_nom["SEL"] == True]
        if not filas_sel.empty:
            st.markdown("---")
            if st.button(f"🚨 ELIMINAR {len(filas_sel)} REGISTRO(S)", type="secondary", use_container_width=False):
                dnis = filas_sel["DNI"].astype(str).tolist()
                for h in dfs:
                    if 'dni' in dfs[h].columns: dfs[h] = dfs[h][~dfs[h]['dni'].astype(str).isin(dnis)]
                save_data(dfs); st.success("Registros eliminados correctamente."); st.rerun()
# ==========================================
    # MÓDULO: REPORTE GENERAL
    # ==========================================
    elif m == "Reporte General": # (Asegúrate de que 'm' sea la variable de tu menú)
        st.markdown("<h2 style='color: #4A0000;'>📊 Reporte General de Trabajadores</h2>", unsafe_allow_html=True)
        
        df_per = dfs.get("PERSONAL", pd.DataFrame())
        df_cont = dfs.get("CONTRATOS", pd.DataFrame())
        df_gen = dfs.get("DATOS GENERALES", pd.DataFrame())
        
        if not df_per.empty and not df_cont.empty:
            # 1. Preparar datos de contratos (Fechas y Cargo)
            df_cont_sorted = df_cont.assign(f_fin_dt=pd.to_datetime(df_cont['f_fin'], errors='coerce')).sort_values('f_fin_dt')
            df_ultimos_contratos = df_cont_sorted.groupby('dni').tail(1)
            
            # 2. Armar la tabla maestra jalando la Sede de Datos Generales
            df_gen = dfs.get("DATOS GENERALES", pd.DataFrame())
            
            # A. Sacamos DNI y Nombres de Personal (Búsqueda inteligente a prueba de balas)
            col_nom_per = next((c for c in df_per.columns if "apellido" in c.lower() or "nombre" in c.lower()), None)
            cols_per = ["dni"]
            if col_nom_per: cols_per.append(col_nom_per)
            master_df = df_per[cols_per].copy()
            
            # B. Jalamos la Sede de Datos Generales
            if not df_gen.empty and "sede" in df_gen.columns:
                master_df = master_df.merge(df_gen[["dni", "sede"]], on="dni", how="left")
            else:
                master_df["sede"] = "No registrada" 
                
            # C. Unimos con los Contratos
            cols_cont = ["dni", "estado", "tipo de trabajador", "modalidad", "temporalidad", "tipo contrato", "cargo", "f_inicio", "f_fin"]
            cols_cont_existentes = [c for c in cols_cont if c in df_ultimos_contratos.columns]
            master_df = master_df.merge(df_ultimos_contratos[cols_cont_existentes], on="dni", how="left")

            # =====================================
            # FILTROS DE BÚSQUEDA
            # =====================================
            st.markdown("### 🔍 Filtros de Búsqueda")
            
            col_est, col_sede = st.columns(2)
            with col_est:
                f_estado = st.multiselect("Estado del Trabajador", options=master_df["estado"].dropna().unique(), default=["ACTIVO"])
            with col_sede:
                # Opciones fijas para que siempre aparezcan
                sedes_opciones = ["Local Giraldez", "Local San Carlos", "Local Abancay", "Local Lince", "Local Pueblo Libre"]
                f_sede = st.multiselect("Sede", options=sedes_opciones)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                f_ttrab = st.multiselect("Tipo de Trabajador", options=master_df.get("tipo de trabajador", pd.Series([])).dropna().unique())
                f_sexo = st.multiselect("Sexo", options=master_df.get("sexo", pd.Series([])).dropna().unique())
            with col2:
                f_mod = st.multiselect("Modalidad", options=master_df.get("modalidad", pd.Series([])).dropna().unique())
                f_ecivil = st.multiselect("Estado Civil", options=master_df.get("estado civil", pd.Series([])).dropna().unique())
            with col3:
                f_temp = st.multiselect("Temporalidad", options=master_df.get("temporalidad", pd.Series([])).dropna().unique())
            with col4:
                f_tcont = st.multiselect("Tipo de Contrato", options=master_df.get("tipo contrato", pd.Series([])).dropna().unique())

            # =====================================
            # APLICAR FILTROS
            # =====================================
            df_filtrado = master_df.copy()
            
            if f_estado: df_filtrado = df_filtrado[df_filtrado["estado"].isin(f_estado)]
            if f_sede and "sede" in df_filtrado.columns: df_filtrado = df_filtrado[df_filtrado["sede"].isin(f_sede)]
            if f_ttrab and "tipo de trabajador" in df_filtrado.columns: df_filtrado = df_filtrado[df_filtrado["tipo de trabajador"].isin(f_ttrab)]
            if f_sexo and "sexo" in df_filtrado.columns: df_filtrado = df_filtrado[df_filtrado["sexo"].isin(f_sexo)]
            if f_mod and "modalidad" in df_filtrado.columns: df_filtrado = df_filtrado[df_filtrado["modalidad"].isin(f_mod)]
            if f_ecivil and "estado civil" in df_filtrado.columns: df_filtrado = df_filtrado[df_filtrado["estado civil"].isin(f_ecivil)]
            if f_temp and "temporalidad" in df_filtrado.columns: df_filtrado = df_filtrado[df_filtrado["temporalidad"].isin(f_temp)]
            if f_tcont and "tipo contrato" in df_filtrado.columns: df_filtrado = df_filtrado[df_filtrado["tipo contrato"].isin(f_tcont)]
          
          # =====================================
            # MOSTRAR TABLA LIMPIA Y ORDENADA
            # =====================================
            st.markdown("---")
            st.success(f"📋 **Resultados:** Se encontraron **{len(df_filtrado)}** trabajadores.")
            
            cols_ideales = ["dni", col_nom_per, "sede", "cargo", "f_inicio", "f_fin", "estado"]
            cols_mostrar = [c for c in cols_ideales if c and c in df_filtrado.columns]
            
            df_display = df_filtrado[cols_mostrar].copy()
            
            # Forzamos el nombre a "Trabajador"
            df_display.rename(columns={
                "dni": "DNI",
                col_nom_per: "Trabajador",
                "sede": "Sede",
                "cargo": "Puesto Laboral",
                "f_inicio": "Inicio Contrato",
                "f_fin": "Fin Contrato",
                "estado": "Estado"
            }, inplace=True)
            
            # TABLA: Ajustada al contenido
            st.dataframe(df_display, hide_index=True, use_container_width=False)
            
            # BOTÓN DE EXPORTAR A EXCEL (REPORTE GENERAL)
            output_gen = BytesIO()
            with pd.ExcelWriter(output_gen, engine='openpyxl') as writer:
                df_display.to_excel(writer, index=False, sheet_name='General')
            st.download_button(
                label="📥 Exportar a Excel", 
                data=output_gen.getvalue(), 
                file_name="Reporte_General.xlsx", 
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                key="btn_exp_gen",
                type="primary"
            )
        else:
            st.warning("⚠️ Necesitas tener datos registrados en Personal y Contratos para generar reportes.")

    # ==========================================
    # MÓDULO: VACACIONES (VERSIÓN ANTIFALLOS)
    # ==========================================
    elif m == "Vacaciones":
        st.markdown("<h2 style='color: #4A0000;'>🌴 Reporte Integrado de Vacaciones</h2>", unsafe_allow_html=True)
        
        df_per = dfs.get("PERSONAL", pd.DataFrame())
        df_vac = dfs.get("VACACIONES", pd.DataFrame())
        df_cont = dfs.get("CONTRATOS", pd.DataFrame())
        df_gen = dfs.get("DATOS GENERALES", pd.DataFrame())

        if df_per.empty or df_vac.empty:
            st.warning("⚠️ No se encontraron las pestañas necesarias (Personal o Vacaciones).")
        else:
            # 1. Normalizar Personal (Limpiar columnas repetidas de raíz)
            df_per.columns = df_per.columns.str.strip().str.lower()
            df_per = df_per.loc[:, ~df_per.columns.duplicated()]
            df_per["dni_key"] = df_per["dni"].astype(str).str.strip().str.replace(".0", "", regex=False).str.zfill(8)
            col_n_p = next((c for c in df_per.columns if "apellido" in c or "nombre" in c), "apellidos y nombres")
            
            # Base del reporte
            df_res = df_per[["dni_key", col_n_p]].copy()

            # 2. SEDE (Datos Generales)
            if not df_gen.empty:
                df_gen.columns = df_gen.columns.str.strip().str.lower()
                df_gen = df_gen.loc[:, ~df_gen.columns.duplicated()]
                df_gen["dni_key"] = df_gen.get("dni", pd.Series(dtype=str)).astype(str).str.strip().str.replace(".0", "", regex=False).str.zfill(8)
                col_s_g = next((c for c in df_gen.columns if "sede" in c), None)
                if col_s_g:
                    df_s = df_gen[["dni_key", col_s_g]].drop_duplicates("dni_key").rename(columns={col_s_g: "Sede"})
                    df_res = df_res.merge(df_s, on="dni_key", how="left")

            # 3. AREA (Contratos)
            if not df_cont.empty:
                df_cont.columns = df_cont.columns.str.strip().str.lower()
                df_cont = df_cont.loc[:, ~df_cont.columns.duplicated()]
                df_cont["dni_key"] = df_cont.get("dni", pd.Series(dtype=str)).astype(str).str.strip().str.replace(".0", "", regex=False).str.zfill(8)
                col_a_c = next((c for c in df_cont.columns if "rea" in c), None)
                if col_a_c:
                    df_a = df_cont.dropna(subset=[col_a_c]).drop_duplicates("dni_key", keep="last")[["dni_key", col_a_c]].rename(columns={col_a_c: "Area_Reporte"})
                    df_res = df_res.merge(df_a, on="dni_key", how="left")

            # 4. DIAS GENERADOS (Vacaciones)
            df_v = df_vac.copy()
            df_v.columns = df_v.columns.str.strip().str.lower()
            
            # --- LA MAGIA: Esto evita el AttributeError y no requiere IFs anidados ---
            df_v = df_v.loc[:, ~df_v.columns.duplicated()] 
            
            c_dni_v = next((c for c in df_v.columns if "dni" in c), None)
            c_dia_v = next((c for c in df_v.columns if "días" in c or "dias" in c), None)
            
            if c_dni_v and c_dia_v:
                df_v["dni_key"] = df_v[c_dni_v].astype(str).str.strip().str.replace(".0", "", regex=False).str.zfill(8)
                # Reemplazamos comas por puntos y convertimos a número de forma segura
                df_v["v_n"] = pd.to_numeric(df_v[c_dia_v].astype(str).str.replace(",", ".", regex=False), errors="coerce").fillna(0.0)
                
                df_v_sum = df_v.groupby("dni_key")["v_n"].sum().reset_index().rename(columns={"v_n": "Días Generados"})
                df_res = df_res.merge(df_v_sum, on="dni_key", how="left")

            # 5. LIMPIEZA POST-MERGE
            if "Sede" not in df_res.columns: df_res["Sede"] = "No registrada"
            if "Area_Reporte" not in df_res.columns: df_res["Area_Reporte"] = "No registrada"
            if "Días Generados" not in df_res.columns: df_res["Días Generados"] = 0.0

            df_res["Sede"] = df_res["Sede"].fillna("No registrada")
            df_res["Area_Reporte"] = df_res["Area_Reporte"].fillna("No registrada")
            df_res["Días Generados"] = df_res["Días Generados"].fillna(0.0)

            # Renombrar DNI y Nombre para la vista
            df_res.rename(columns={"dni_key": "DNI", col_n_p: "Trabajador", "Area_Reporte": "Área"}, inplace=True)

            # 6. FILTROS
            st.markdown("### 🔍 Filtros")
            c1, c2 = st.columns(2)
            
            # Quitamos los 'nan' de las listas para que se vea profesional
            with c1:
                s_list = ["Todas"] + sorted([str(x) for x in df_res["Sede"].unique() if str(x) != "nan"])
                sel_s = st.selectbox("Sede", s_list)
            with c2:
                a_list = ["Todas"] + sorted([str(x) for x in df_res["Área"].unique() if str(x) != "nan"])
                sel_a = st.selectbox("Área", a_list)

            df_f = df_res.copy()
            if sel_s != "Todas": df_f = df_f[df_f["Sede"] == sel_s]
            if sel_a != "Todas": df_f = df_f[df_f["Área"] == sel_a]

            # 7. TABLA FINAL
            st.success(f"📋 Registros encontrados: {len(df_f)}")
            
            cols_ver = ["DNI", "Trabajador", "Sede", "Área", "Días Generados"]
            st.dataframe(
                df_f[cols_ver].style.format({"Días Generados": "{:.2f}"}),
                hide_index=True,
                use_container_width=True
            )
            
            # 8. BOTÓN DE DESCARGA EXCEL
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_f[cols_ver].to_excel(writer, index=False, sheet_name='Vacaciones')
            st.download_button(
                label="📥 Exportar a Excel", 
                data=output.getvalue(), 
                file_name="Reporte_Vacaciones_Antifallos.xlsx", 
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="btn_exp_vac_antifallos",
                type="primary"
            )
# ==========================================
    # MÓDULO: CUMPLEAÑEROS
    # ==========================================
    elif m == "Cumpleañeros":
        st.markdown("<h2 style='color: #4A0000;'>🎂 Reporte de Cumpleañeros</h2>", unsafe_allow_html=True)
        
        df_per = dfs.get("PERSONAL", pd.DataFrame())
        df_gen = dfs.get("DATOS GENERALES", pd.DataFrame())
        
        if not df_per.empty and not df_gen.empty:
            col_fnac = next((c for c in df_gen.columns if "nacimiento" in c.lower() and "fecha" in c.lower()), None)
            
            if col_fnac:
                col_nom_per = next((c for c in df_per.columns if "apellido" in c.lower() or "nombre" in c.lower()), None)
                cols_per = ["dni"]
                if col_nom_per: cols_per.append(col_nom_per)
                df_cumple = df_per[cols_per].copy()
                
                cols_gen_a_jalar = ["dni", col_fnac]
                if "sede" in df_gen.columns: cols_gen_a_jalar.append("sede")
                
                df_cumple = df_cumple.merge(df_gen[cols_gen_a_jalar], on="dni", how="inner")
                if "sede" not in df_cumple.columns: df_cumple["sede"] = "No registrada"
                
                df_cumple[col_fnac] = pd.to_datetime(df_cumple[col_fnac], errors="coerce")
                df_cumple = df_cumple.dropna(subset=[col_fnac])
                
                # Cálculos de meses en Español
                meses = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
                df_cumple["Mes_Num"] = df_cumple[col_fnac].dt.month
                df_cumple["Mes"] = df_cumple["Mes_Num"].map(meses)
                
                año_actual = date.today().year
                df_cumple["Años a cumplir"] = año_actual - df_cumple[col_fnac].dt.year
                
                # Formato en Español: "15 de Octubre"
                df_cumple["Fecha de cumpleaños"] = df_cumple[col_fnac].dt.day.astype(str) + " de " + df_cumple["Mes"]
                
                # Filtros
                col1, col2 = st.columns(2)
                with col1:
                    sedes_opciones = ["Local Giraldez", "Local San Carlos", "Local Abancay", "Local Lince", "Local Pueblo Libre"]
                    f_sede = st.multiselect("Sede", options=sedes_opciones)
                with col2:
                    f_mes = st.multiselect("Mes", options=list(meses.values()))
                
                if f_sede and "sede" in df_cumple.columns: df_cumple = df_cumple[df_cumple["sede"].isin(f_sede)]
                if f_mes: df_cumple = df_cumple[df_cumple["Mes"].isin(f_mes)]
                
                df_cumple = df_cumple.sort_values("Mes_Num")
                df_cumple.rename(columns={"dni": "DNI", col_nom_per: "Trabajador", "sede": "Sede"}, inplace=True)
                
                st.markdown("---")
                st.dataframe(df_cumple[["DNI", "Trabajador", "Sede", "Fecha de cumpleaños", "Años a cumplir"]].style.set_properties(**{'font-size': '15px'}), hide_index=True, use_container_width=False)
                # BOTÓN DE EXPORTAR A EXCEL (CUMPLEAÑEROS)
                df_export_cump = df_cumple[["DNI", "Trabajador", "Sede", "Fecha de cumpleaños", "Años a cumplir"]].copy()
                output_cump = BytesIO()
                with pd.ExcelWriter(output_cump, engine='openpyxl') as writer:
                    df_export_cump.to_excel(writer, index=False, sheet_name='Cumpleañeros')
                st.download_button(label="📥 Exportar a Excel", data=output_cump.getvalue(), file_name="Reporte_Cumpleañeros.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="btn_exp_cump")
            else:
                st.warning("⚠️ No se encontró la columna de 'Fecha de nacimiento' en Datos Generales.")
        else:
            st.warning("⚠️ Faltan datos en Personal o Datos Generales.")

    elif m == "Vacaciones":
        st.markdown("<h2 style='color: #4A0000;'>🌴 Reporte Integrado de Vacaciones</h2>", unsafe_allow_html=True)
        
        df_per = dfs.get("PERSONAL", pd.DataFrame())
        df_vac = dfs.get("VACACIONES", pd.DataFrame())
        df_gen = dfs.get("DATOS GENERALES", pd.DataFrame())
        df_cont = dfs.get("CONTRATOS", pd.DataFrame())

        if df_per.empty or df_vac.empty:
            st.warning("⚠️ No se encontraron datos en PERSONAL o VACACIONES.")
        else:
            # Preparar DNI puente
            df_per["DNI_KEY"] = df_per["dni"].astype(str).str.strip().str.replace(".0", "", regex=False).str.zfill(8)
            col_nom = next((c for c in df_per.columns if "nombre" in c.lower() or "apellido" in c.lower()), "apellidos y nombres")
            
            # Base limpia
            df_res = df_per[["DNI_KEY", col_nom]].copy()

            # AREA y SEDE (Desde DATOS GENERALES)
            if not df_gen.empty:
                df_gen["DNI_KEY"] = df_gen["dni"].astype(str).str.strip().str.replace(".0", "", regex=False).str.zfill(8)
                cols_gen = []
                if "sede" in df_gen.columns: cols_gen.append("sede")
                if "area" in df_gen.columns: cols_gen.append("area")
                
                if cols_gen:
                    temp_gen = df_gen[["DNI_KEY"] + cols_gen].drop_duplicates("DNI_KEY")
                    df_res = df_res.merge(temp_gen, on="DNI_KEY", how="left")

            # Si AREA sigue vacía, buscar en CONTRATOS
            if "area" not in df_res.columns and not df_cont.empty:
                df_cont["DNI_KEY"] = df_cont["dni"].astype(str).str.strip().str.replace(".0", "", regex=False).str.zfill(8)
                if "area" in df_cont.columns:
                    temp_cont = df_cont[["DNI_KEY", "area"]].dropna(subset=["area"]).drop_duplicates("DNI_KEY", keep="last")
                    df_res = df_res.merge(temp_cont, on="DNI_KEY", how="left")
            elif "area" not in df_res.columns:
                df_res["area"] = "No registrada"

            if "sede" not in df_res.columns: df_res["sede"] = "No registrada"

            # CÁLCULO DE DÍAS GOZADOS (Vacaciones)
            c_dia_g = next((c for c in df_v.columns if "dia" in c.lower() and "goz" in c.lower()), None)
            
            if c_dia_g:
                df_v["g_n"] = pd.to_numeric(df_v[c_dia_g].astype(str).str.replace(",", "."), errors="coerce").fillna(0)
                df_sum_g = df_v.groupby("DNI_KEY")["g_n"].sum().reset_index().rename(columns={"g_n": "DÍAS GOZADOS"})
                df_res = df_res.merge(df_sum_g, on="DNI_KEY", how="left")
            else:
                df_res["DÍAS GOZADOS"] = 0.0

            # CÁLCULO DE DÍAS GOZADOS
            c_dia_g = next((c for c in df_v.columns if "dia" in c.lower() and "goz" in c.lower()), None)
            
            if c_dia_g:
                if isinstance(df_v[c_dia_g], pd.DataFrame):
                    col_goz_segura = df_v[c_dia_g].iloc[:, 0]
                else:
                    col_goz_segura = df_v[c_dia_g]
                    
                df_v["g_n"] = pd.to_numeric(col_goz_segura.astype(str).str.replace(",", ".", regex=False), errors="coerce").fillna(0.0)
                df_sum_g = df_v.groupby("DNI_KEY")["g_n"].sum().reset_index().rename(columns={"g_n": "DÍAS GOZADOS"})
                df_res = df_res.merge(df_sum_g, on="DNI_KEY", how="left")
            else:
                df_res["DÍAS GOZADOS"] = 0.0

            # Limpiar Nulos y Calcular Saldo
            df_res["DÍAS GENERADOS"] = df_res["DÍAS GENERADOS"].fillna(0.0)
            df_res["DÍAS GOZADOS"] = df_res["DÍAS GOZADOS"].fillna(0.0)
            df_res["SALDO"] = df_res["DÍAS GENERADOS"] - df_res["DÍAS GOZADOS"]

            # Renombrar para presentación final
            df_res = df_res.rename(columns={
                "DNI_KEY": "DNI",
                col_nom: "TRABAJADOR",
                "sede": "SEDE",
                "area": "AREA"
            })
            
            df_res.columns = [str(c).upper() for c in df_res.columns]

            # Filtros Interactivos
            st.markdown("### 🔍 Filtros")
            c1, c2 = st.columns(2)
            
            sedes_unicas = ["TODAS"] + sorted([str(x) for x in df_res["SEDE"].dropna().unique() if str(x) != 'nan'])
            areas_unicas = ["TODAS"] + sorted([str(x) for x in df_res["AREA"].dropna().unique() if str(x) != 'nan'])
            
            with c1:
                f_s = st.selectbox("Sede", sedes_unicas)
            with c2:
                f_a = st.selectbox("Área", areas_unicas)

            # Aplicar Filtros
            df_f = df_res.copy()
            if f_s != "TODAS": df_f = df_f[df_f["SEDE"] == f_s]
            if f_a != "TODAS": df_f = df_f[df_f["AREA"] == f_a]

            # Mostrar Tabla
            st.markdown("---")
            st.success(f"📋 **Total de registros encontrados:** {len(df_f)}")
            st.dataframe(df_f.style.format({
                "DÍAS GENERADOS": "{:.2f}",
                "DÍAS GOZADOS": "{:.2f}",
                "SALDO": "{:.2f}"
            }), hide_index=True, use_container_width=True)

            # Botón de Exportar
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_f.to_excel(writer, index=False, sheet_name='Vacaciones')
            st.download_button(
                label="📥 Exportar a Excel", 
                data=output.getvalue(), 
                file_name="Reporte_Vacaciones.xlsx", 
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="btn_exp_vac_final",
                type="primary"
            )
# ==========================================
    # MÓDULO: VENCIMIENTO DE CONTRATOS
    # ==========================================
    elif m == "Vencimientos":
        st.markdown("<h2 style='color: #4A0000;'>⏳ Reporte de Vencimiento de Contratos</h2>", unsafe_allow_html=True)
        
        df_per = dfs.get("PERSONAL", pd.DataFrame())
        df_cont = dfs.get("CONTRATOS", pd.DataFrame())
        df_gen = dfs.get("DATOS GENERALES", pd.DataFrame())
        
        if not df_per.empty and not df_cont.empty:
            # 1. Base: DNI y Nombres
            col_nom_per = next((c for c in df_per.columns if "apellido" in c.lower() or "nombre" in c.lower()), None)
            cols_per = ["dni"]
            if col_nom_per: cols_per.append(col_nom_per)
            df_venc = df_per[cols_per].copy()
            
            # 2. Sede (de Datos Generales)
            if not df_gen.empty and "sede" in df_gen.columns:
                df_venc = df_venc.merge(df_gen[["dni", "sede"]], on="dni", how="left")
            else:
                df_venc["sede"] = "No registrada"
                
            # 3. Datos del último contrato
            df_cont_sorted = df_cont.assign(f_fin_dt=pd.to_datetime(df_cont['f_fin'], errors='coerce')).sort_values('f_fin_dt')
            df_ultimos_contratos = df_cont_sorted.groupby('dni').tail(1)
            
            cols_cont_necesarias = ["dni", "cargo", "area", "f_fin", "tipo de trabajador", "tipo contrato"]
            cols_existentes = [c for c in cols_cont_necesarias if c in df_ultimos_contratos.columns]
            
            # Unimos solo los que tienen contrato
            df_venc = df_venc.merge(df_ultimos_contratos[cols_existentes], on="dni", how="inner") 
            
            # 4. Formatear la fecha y extraer el Mes
            df_venc["f_fin_dt"] = pd.to_datetime(df_venc["f_fin"], errors="coerce")
            meses_dict = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
            df_venc["Mes de Vencimiento"] = df_venc["f_fin_dt"].dt.month.map(meses_dict)
            
            # Renombrar para que se vea bien
            rename_dict = {
                "dni": "DNI",
                col_nom_per: "Trabajador",
                "sede": "Sede",
                "cargo": "Puesto",
                "AREA": "AREA",
                "f_fin": "Fecha de Vencimiento",
                "tipo de trabajador": "Tipo de Trabajador",
                "tipo contrato": "Tipo de Contrato"
            }
            df_venc.rename(columns=rename_dict, inplace=True)
            
            # 5. Filtros de Búsqueda
            col1, col2, col3 = st.columns(3)
            with col1:
                sedes_opciones = ["Local Giraldez", "Local San Carlos", "Local Abancay", "Local Lince", "Local Pueblo Libre"]
                f_sede = st.multiselect("Sede", options=sedes_opciones)
                areas_disp = df_venc["AREA"].dropna().unique() if "AREA" in df_venc.columns else []
                f_area = st.multiselect("AREA", options=areas_disp)
            with col2:
                f_mes = st.multiselect("Mes de Vencimiento", options=list(meses_dict.values()))
                tipos_trab = df_venc["Tipo de Trabajador"].dropna().unique() if "Tipo de Trabajador" in df_venc.columns else []
                f_ttrab = st.multiselect("Tipo de Trabajador", options=tipos_trab)
            with col3:
                tipos_cont = df_venc["Tipo de Contrato"].dropna().unique() if "Tipo de Contrato" in df_venc.columns else []
                f_tcont = st.multiselect("Tipo de Contrato", options=tipos_cont)
                
            # 6. Aplicar filtros
            if f_sede and "Sede" in df_venc.columns: df_venc = df_venc[df_venc["Sede"].isin(f_sede)]
            if f_area and "area" in df_venc.columns: df_venc = df_venc[df_venc["AREA"].isin(f_area)]
            if f_mes and "Mes de Vencimiento" in df_venc.columns: df_venc = df_venc[df_venc["Mes de Vencimiento"].isin(f_mes)]
            if f_ttrab and "Tipo de Trabajador" in df_venc.columns: df_venc = df_venc[df_venc["Tipo de Trabajador"].isin(f_ttrab)]
            if f_tcont and "Tipo de Contrato" in df_venc.columns: df_venc = df_venc[df_venc["Tipo de Contrato"].isin(f_tcont)]
            
            # Ordenar por fecha más próxima a vencer
            df_venc = df_venc.sort_values(by="f_fin_dt", na_position="last")
            
            # 7. Mostrar la Tabla
            cols_finales = ["DNI", "Trabajador", "Puesto", "Sede", "AREA", "Tipo de Trabajador", "Tipo de Contrato", "Fecha de Vencimiento", "Mes de Vencimiento"]
            cols_mostrar = [c for c in cols_finales if c in df_venc.columns]
            
            df_final = df_venc[cols_mostrar].copy()
            
            st.markdown("---")
            st.success(f"📋 **Resultados:** {len(df_final)} contratos encontrados.")
            st.dataframe(df_final, hide_index=True, use_container_width=False)
            
            # 8. Botón Exportar a Excel
            output_venc = BytesIO()
            with pd.ExcelWriter(output_venc, engine='openpyxl') as writer:
                df_final.to_excel(writer, index=False, sheet_name='Vencimientos')
            st.download_button(
                label="📥 Exportar a Excel", 
                data=output_venc.getvalue(), 
                file_name="Reporte_Vencimientos.xlsx", 
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="btn_exp_venc",
                type="primary"
            )
        else:
            st.warning("⚠️ Faltan datos en Personal o Contratos para generar este reporte.")






















































































































































