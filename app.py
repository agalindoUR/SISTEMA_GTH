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
    "PERSONAL": ["dni", "apellidos y nombres", "link"],
    "DATOS GENERALES": ["apellidos y nombres", "dni", "sexo", "dirección", "link de dirección", "departamento residencia", "provincia residencia", "distrito residencia", "departamento nacimiento", "provincia nacimiento", "distrito nacimiento", "estado civil", "fecha de nacimiento", "edad"],
    "DATOS FAMILIARES": ["parentesco", "apellidos y nombres", "dni", "fecha de nacimiento", "edad", "estudios", "telefono"],
    "EXP. LABORAL": ["tipo de experiencia", "lugar", "puesto", "fecha inicio", "fecha de fin", "motivo cese"],
    "FORM. ACADEMICA": ["grado, titulo o especialización", "descripcion", "universidad", "año"],
    "INVESTIGACION": ["año publicación", "autor, coautor o asesor", "tipo de investigación publicada", "nivel de publicación", "lugar de publicación"],
    # NUEVAS COLUMNAS DE CONTRATOS APLICADAS:
    "CONTRATOS": ["id", "dni", "cargo", "remuneración básica", "bonificación", "condición de trabajo", "f_inicio", "f_fin", "tipo de trabajador", "modalidad", "temporalidad", "link", "tipo contrato", "estado", "motivo cese"],
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
    for h, cols in COLUMNAS.items():
        if h in hojas_existentes:
            worksheet = hojas_existentes[h]
            data = worksheet.get_all_records()
            df = pd.DataFrame(data) if data else pd.DataFrame(columns=cols)
        else:
            # Si la hoja no existe, la crea
            worksheet = sheet.add_worksheet(title=h, rows="100", cols="20")
            worksheet.append_row([c.upper() for c in cols])
            df = pd.DataFrame(columns=cols)

        # ... (A partir de aquí, deja el resto de tu código igual: df.columns = ...)
        df.columns = [str(c).strip().lower() for c in df.columns]
                  
        if h == "CONTRATOS":
            if "sueldo" in df.columns: df.rename(columns={"sueldo": "remuneración básica"}, inplace=True)
            if "tipo colaborador" in df.columns: df.rename(columns={"tipo colaborador": "tipo de trabajador"}, inplace=True)
            if "tipo" in df.columns and "tipo de trabajador" not in df.columns: df.rename(columns={"tipo": "tipo de trabajador"}, inplace=True)

        if "dni" in df.columns:
            df["dni"] = df["dni"].astype(str).str.strip().replace(r'\.0$', '', regex=True)
        
        for req_col in cols:
            if req_col not in df.columns: df[req_col] = None
            
        dfs[h] = df
    return dfs

def save_data(dfs):
    creds = obtener_credenciales()
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME)

    for h, df in dfs.items():
        worksheet = sheet.worksheet(h)
        df_s = df.copy()
        df_s = df_s.fillna("")
        df_s = df_s.astype(str).replace("nan", "")
        df_s.columns = [c.upper() for c in df_s.columns]
        
        worksheet.clear()
        worksheet.update([df_s.columns.values.tolist()] + df_s.values.tolist())
    
    # <--- AGREGA ESTA LÍNEA AQUÍ (Fuera del for, al final de la función)
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
        if os.path.exists("Logo_amarillo.png"): st.image("Logo_amarillo.png", use_container_width=True)

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
            if os.path.exists("Logo_guindo.png"): st.image("Logo_guindo.png", use_container_width=True)
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("### 🛠️ MENÚ PRINCIPAL")
        m = st.radio("", ["🔍 Consulta", "➕ Registro", "📊 Nómina General"], key="menu_p_unico")
        st.markdown("### 📈 REPORTES")
        r = st.radio("", ["Vencimientos", "Vacaciones", "Estadísticas"], key="menu_r_unico")
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
                        ed = st.data_editor(vst, hide_index=True, use_container_width=True, column_config=col_conf, key=f"ed_{h_name}")
                        sel = ed[ed["SEL"] == True]

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

                            if st.button(f"📄 Generar Papeleta de Impresión (Periodo {p_papeleta})", key="btn_print_vaca_tab", use_container_width=True):
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

                                            if st.button("💾 Guardar Registro de Vacaciones", type="primary", use_container_width=True):
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
                                                    update_vals = {"cargo": n_car, "remuneración básica": n_rem, "bonificación": n_bon, "condición de trabajo": n_cond, "f_inicio": n_ini, "f_fin": n_fin, "tipo de trabajador": n_ttrab, "modalidad": n_mod, "temporalidad": n_tem, "link": n_lnk, "tipo contrato": n_tcont, "estado": est_e, "motivo cese": mot_e}
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
            d_dni = st.text_input("DNI").strip()
            # 1. Separamos Apellidos y Nombres (Asegurando Mayúsculas)
            ape_form = st.text_input("Apellidos").upper().strip()
            nom_form = st.text_input("Nombres").upper().strip()
            # Combinamos para "apellidos y nombres" (Apellido, Nombre)
            nom_comp = f"{ape_form}, {nom_form}" if ape_form and nom_form else ""
            # 2. Listas desglosables
            sexo_form = st.selectbox("Sexo", ["Masculino", "Femenino"])
            estado_form = st.selectbox("Estado Civil", ["Soltero(a)", "Casado(a)", "Divorciado(a)", "Conviviente", "Viudo(a)", "Otro"])
            sede_form = st.selectbox("Sede de Trabajo", ["Local Giraldez", "Local San Carlos", "Local Abancay", "Local Lince", "Local Pueblo Libre"])
            link_form = st.text_input("Link File").strip()

            if st.form_submit_button("Registrar"):
                if d_dni and ape_form and nom_form:
                    # Cálculo robusto del ID para PERSONAL (ID único por persona)
                    next_id_personal = dfs["PERSONAL"]["id"].max() + 1 if not dfs["PERSONAL"].empty else 1
                    # A. Guardamos en PERSONAL (Lista Maestra)
                    nuevo_personal = {"id": next_id_personal, "dni": d_dni, "apellidos": ape_form, "nombres": nom_form, "apellidos y nombres": nom_comp, "sexo": sexo_form, "estado_civil": estado_form, "sede": sede_form, "link": link_form}
                    dfs["PERSONAL"] = pd.concat([dfs["PERSONAL"], pd.DataFrame([nuevo_personal])], ignore_index=True)
                    
                    # CORRECCIÓN VINCULACIÓN: Crear automáticamente entrada básica en DATOS GENERALES
                    # El ID debe coincidir o ser único por sheet, optamos por ID único por sheet y vinculación por DNI
                    nid_dg = dfs["DATOS GENERALES"]["id"].max() + 1 if not dfs["DATOS GENERALES"].empty else 1
                    nuevo_dg_basico = {"id": nid_dg, "dni": d_dni, "apellidos y nombres": nom_comp}
                    dfs["DATOS GENERALES"] = pd.concat([dfs["DATOS GENERALES"], pd.DataFrame([nuevo_dg_basico])], ignore_index=True)
                    
                    # Guardamos ambos cambios
                    save_data(dfs)
                    st.success("Trabajador registrado correctamente")
                    st.rerun()
                else: st.error("⚠️ Por favor, complete al menos el DNI, Apellidos y Nombres.")

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
        ed_nom = st.data_editor(df_ver, hide_index=True, use_container_width=True, key="nomina_v3_blanco")
        filas_sel = ed_nom[ed_nom["SEL"] == True]
        if not filas_sel.empty:
            st.markdown("---")
            if st.button(f"🚨 ELIMINAR {len(filas_sel)} REGISTRO(S)", type="secondary", use_container_width=True):
                dnis = filas_sel["DNI"].astype(str).tolist()
                for h in dfs:
                    if 'dni' in dfs[h].columns: dfs[h] = dfs[h][~dfs[h]['dni'].astype(str).isin(dnis)]
                save_data(dfs); st.success("Registros eliminados correctamente."); st.rerun()
# ==========================================
# MÓDULO DE REPORTES Y FILTROS AVANZADOS
# ==========================================
elif m == "Reportes":
    st.markdown("<h2 style='color: #4A0000;'>📊 Reportes y Filtros Avanzados</h2>", unsafe_allow_html=True)
    
    df_per = dfs.get("PERSONAL", pd.DataFrame())
    df_cont = dfs.get("CONTRATOS", pd.DataFrame())
    df_gen = dfs.get("DATOS GENERALES", pd.DataFrame())
    df_fam = dfs.get("DATOS FAMILIARES", pd.DataFrame())
    
    if not df_per.empty and not df_cont.empty:
        df_cont_sorted = df_cont.assign(f_fin_dt=pd.to_datetime(df_cont['f_fin'], errors='coerce')).sort_values('f_fin_dt')
        df_ultimos_contratos = df_cont_sorted.groupby('dni').tail(1)
        
        df_hijos = pd.DataFrame(columns=["dni", "tiene_hijos"])
        if not df_fam.empty and "parentesco" in df_fam.columns:
            hijos_mask = df_fam["parentesco"].fillna("").str.lower().str.contains("hijo|hija")
            dnis_con_hijos = df_fam[hijos_mask]["dni"].unique()
            df_hijos = pd.DataFrame({"dni": dnis_con_hijos, "tiene_hijos": "Sí"})
        
        master_df = df_per[["dni", "apellidos y nombres"]].merge(
            df_ultimos_contratos[["dni", "estado", "tipo de trabajador", "modalidad", "temporalidad", "tipo contrato"]], 
            on="dni", how="left"
        )
        
        if not df_gen.empty:
            cols_gen = ["dni", "sexo", "estado civil", "departamento residencia", "provincia residencia", "distrito residencia", "departamento nacimiento", "provincia nacimiento", "distrito nacimiento"]
            cols_existentes = [c for c in cols_gen if c in df_gen.columns]
            master_df = master_df.merge(df_gen[cols_existentes], on="dni", how="left")
            
        master_df = master_df.merge(df_hijos, on="dni", how="left")
        master_df["tiene_hijos"] = master_df["tiene_hijos"].fillna("No")
        master_df["estado"] = master_df["estado"].fillna("SIN CONTRATO")

        st.markdown("### 🔍 Filtros de Búsqueda")
        
        f_estado = st.multiselect("Estado del Trabajador", options=master_df["estado"].dropna().unique(), default=["ACTIVO"])
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            f_ttrab = st.multiselect("Tipo de Trabajador", options=master_df["tipo de trabajador"].dropna().unique())
            f_sexo = st.multiselect("Sexo", options=master_df.get("sexo", pd.Series([])).dropna().unique())
        with col2:
            f_mod = st.multiselect("Modalidad", options=master_df["modalidad"].dropna().unique())
            f_ecivil = st.multiselect("Estado Civil", options=master_df.get("estado civil", pd.Series([])).dropna().unique())
        with col3:
            f_temp = st.multiselect("Temporalidad", options=master_df["temporalidad"].dropna().unique())
            f_hijos = st.multiselect("¿Tiene Hijos?", options=["Sí", "No"])
        with col4:
            f_tcont = st.multiselect("Tipo de Contrato", options=master_df["tipo contrato"].dropna().unique())

        st.markdown("#### 📍 Filtros de Ubicación")
        col_u1, col_u2 = st.columns(2)
        with col_u1:
            f_d_res = st.multiselect("Distrito de Residencia", options=master_df.get("distrito residencia", pd.Series([])).dropna().unique())
        with col_u2:
            f_d_nac = st.multiselect("Distrito de Nacimiento", options=master_df.get("distrito nacimiento", pd.Series([])).dropna().unique())

        df_filtrado = master_df.copy()
        
        if f_estado: df_filtrado = df_filtrado[df_filtrado["estado"].isin(f_estado)]
        if f_ttrab: df_filtrado = df_filtrado[df_filtrado["tipo de trabajador"].isin(f_ttrab)]
        if f_sexo and "sexo" in df_filtrado.columns: df_filtrado = df_filtrado[df_filtrado["sexo"].isin(f_sexo)]
        if f_mod: df_filtrado = df_filtrado[df_filtrado["modalidad"].isin(f_mod)]
        if f_ecivil and "estado civil" in df_filtrado.columns: df_filtrado = df_filtrado[df_filtrado["estado civil"].isin(f_ecivil)]
        if f_temp: df_filtrado = df_filtrado[df_filtrado["temporalidad"].isin(f_temp)]
        if f_hijos: df_filtrado = df_filtrado[df_filtrado["tiene_hijos"].isin(f_hijos)]
        if f_tcont: df_filtrado = df_filtrado[df_filtrado["tipo contrato"].isin(f_tcont)]
        if f_d_res and "distrito residencia" in df_filtrado.columns: df_filtrado = df_filtrado[df_filtrado["distrito residencia"].isin(f_d_res)]
        if f_d_nac and "distrito nacimiento" in df_filtrado.columns: df_filtrado = df_filtrado[df_filtrado["distrito nacimiento"].isin(f_d_nac)]

        st.markdown("---")
        st.success(f"📋 **Resultados:** Se encontraron **{len(df_filtrado)}** trabajadores que cumplen los criterios.")
        
        st.dataframe(
            df_filtrado, 
            hide_index=True, 
            use_container_width=True,
            column_config={
                "dni": None,
                "apellidos y nombres": st.column_config.TextColumn("Trabajador", width="large")
            }
        )
    else:
        st.warning("⚠️ Necesitas tener datos registrados en Personal y Contratos para generar reportes.")








































































