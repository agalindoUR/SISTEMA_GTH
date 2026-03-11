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
    "DATOS GENERALES": ["dni", "sede", "sexo", "apellidos y nombres", "dirección", "estado civil", "fecha de nacimiento", "edad"], 
    "DATOS FAMILIARES": ["parentesco", "apellidos y nombres", "dni", "fecha de nacimiento", "edad", "estudios", "telefono"],
    "EXP. LABORAL": ["tipo de experiencia", "lugar", "puesto", "fecha inicio", "fecha de fin", "motivo cese"],
    "FORM. ACADEMICA": ["grado, titulo o especialización", "descripcion", "universidad", "año"],
    "INVESTIGACION": ["año publicación", "autor, coautor o asesor", "tipo de investigación publicada", "nivel de publicación", "lugar de publicación"],
    # NUEVAS COLUMNAS DE CONTRATOS APLICADAS:
    "CONTRATOS": ["dni", "cargo", "AREA", "f_inicio", "f_fin", "tipo de trabajador", "modalidad", "temporalidad", "tipo contrato", "estado", "LINK"],
    "IONES": ["periodo", "fecha de inicio", "fecha de fin", "días generados", "días gozados", "saldo", "link"],
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
    # --- TRUCO: Convertimos columnas a minúsculas solo para el Word ---
    df_c = df_c.copy()
    df_c.columns = [str(c).strip().lower() for c in df_c.columns]
    
    # ... aquí sigue el resto de tu código normal:
    # df_c['f_inicio'] = pd.to_datetime(df_c['f_inicio'], errors='coerce')
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
# FUNCIÓN 2: GENERAR PAPELETA DE IONES INDIVIDUAL (Word Duplicado A4)
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
        st.radio("Reportes", ["Reporte General", "Cumpleañeros", "iones", "Vencimientos"], key="menu_r", on_change=click_menu_r, index=None, label_visibility="collapsed")
        
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

                # Línea 497: El bucle for
            for i, tab in enumerate(tabs):
                # Línea 498: AHORA ESTÁ INDENTADA (4 espacios más que el for)
                h_name = h_keys[i]
                with tab:
                    # NORMALIZACIÓN TOTAL: Forzamos minúsculas para trabajar internamente
                    dfs[h_name].columns = [str(c).lower().strip() for c in dfs[h_name].columns]
                    
                    # Filtro de DNI ultra-robusto
                    if "dni" in dfs[h_name].columns:
                        c_df = dfs[h_name][dfs[h_name]["dni"].astype(str).str.strip() == str(dni_buscado).strip()]
                    else:
                        c_df = pd.DataFrame(columns=COLUMNAS.get(h_name, []))
                    
                    # A partir de aquí sigue el resto de tu código de visualización...
                    # 2. Lógica específica para la pestaña CONTRATOS
                    if h_name == "CONTRATOS":
                        # Limpieza de nombres de columnas para evitar espacios invisibles
                        dfs["CONTRATOS"].columns = [str(c).strip().upper() for c in dfs["CONTRATOS"].columns]
                        
                        # Verificación de existencia de columna DNI
                        if "DNI" not in dfs["CONTRATOS"].columns:
                            st.error(f"🚨 ALERTA: No se encuentra la columna 'DNI' en CONTRATOS. Columnas detectadas: {list(dfs['CONTRATOS'].columns)}")
                            st.stop()
                            
                        # Filtrado riguroso para el Certificado
                        df_contratos = dfs["CONTRATOS"][dfs["CONTRATOS"]["DNI"].astype(str).str.strip() == str(dni_buscado).strip()]
                        
                        if not df_contratos.empty:
                            # Estilo personalizado para el botón de descarga
                            st.markdown("""
                                <style>
                                [data-testid="stDownloadButton"] button { background-color: #FFD700 !important; border: 2px solid #4A0000 !important; }
                                [data-testid="stDownloadButton"] button p { color: #4A0000 !important; font-weight: bold !important; font-size: 16px !important; }
                                [data-testid="stDownloadButton"] button:hover { background-color: #ffffff !important; border: 2px solid #FFD700 !important; }
                                </style>
                            """, unsafe_allow_html=True)
                            
                            # Generación y botón de descarga del Certificado
                            # Se añade una key única para evitar errores de DuplicatedElement
                            word_file = gen_word(nom_c, dni_buscado, df_contratos)
                            if word_file:
                                st.download_button(
                                    label="📄 Generar Certificado de Trabajo", 
                                    data=word_file, 
                                    file_name=f"Certificado_{dni_buscado}.docx", 
                                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                    key=f"btn_cert_{dni_buscado}"
                                )
                            st.markdown("<br>", unsafe_allow_html=True)

                    # 3. Visualización de la tabla (ESTO DEBE ESTAR ALINEADO CON LOS IF DE ARRIBA)
                    # ==========================================
                    # 1. PREPARACIÓN DE DATOS (COMÚN PARA TODAS LAS PESTAÑAS)
                    # ==========================================
                    if not c_df.empty:
                        # Estandarizamos para cálculos internos
                        c_df.columns = [str(c).lower().strip() for c in c_df.columns]
                        
                        detalles = []
                        dias_generados_totales = 0
                        dias_gozados_totales = 0

                       # ==========================================================
                        # BLOQUE ÚNICO Y DEFINITIVO DE VACACIONES (CON SANGRÍA CORRECTA)
                        # ==========================================================
                        if h_name == "VACACIONES":
                            detalles = []
                            dias_generados_totales = 0
                            
                            # 1. Preparación de datos (Evita el KeyError)
                            c_df_interna = c_df.copy()
                            c_df_interna.columns = [c.lower().strip() for c in c_df_interna.columns]
                            dias_gozados_totales = pd.to_numeric(c_df_interna.get("días gozados", 0), errors='coerce').sum()

                            # 2. Lógica de cálculo de periodos
                            df_tc = df_contratos[df_contratos["TIPO CONTRATO"].astype(str).str.lower().str.contains("planilla", na=False)] if not df_contratos.empty else pd.DataFrame()
                            
                            if not df_tc.empty:
                                df_tc_calc = df_tc.copy()
                                df_tc_calc.columns = [c.upper() for c in df_tc_calc.columns]
                                df_tc_calc['f_inicio_dt'] = pd.to_datetime(df_tc_calc['F_INICIO'], errors='coerce')
                                start_global = df_tc_calc['f_inicio_dt'].min()
                                
                                if pd.notnull(start_global):
                                    curr_start = start_global.date()
                                    while curr_start <= date.today():
                                        curr_end = (pd.to_datetime(curr_start) + pd.DateOffset(years=1) - pd.Timedelta(days=1)).date()
                                        days_in_p = 0
                                        for _, r in df_tc_calc.iterrows():
                                            c_s = r['f_inicio_dt'].date() if pd.notnull(r['f_inicio_dt']) else None
                                            c_e = pd.to_datetime(r.get('F_FIN'), errors='coerce').date() if pd.notnull(r.get('F_FIN')) else date.today()
                                            if c_s:
                                                o_s, o_e = max(curr_start, c_s), min(curr_end, c_e, date.today())
                                                if o_s <= o_e: days_in_p += (o_e - o_s).days + 1
                                        
                                        total_days = (curr_end - curr_start).days + 1
                                        gen_p = round((days_in_p / total_days) * 30, 2)
                                        p_name = f"{curr_start.year}-{curr_start.year+1}"
                                        
                                        # Buscar días gozados usando la columna en minúsculas
                                        goz_p = pd.to_numeric(c_df_interna[c_df_interna["periodo"].astype(str).str.strip() == p_name]["días gozados"], errors='coerce').sum()
                                        
                                        detalles.append({
                                            "PERIODO": p_name, 
                                            "DEL": curr_start.strftime("%d/%m/%Y"), 
                                            "AL": curr_end.strftime("%d/%m/%Y"),
                                            "DÍAS GENERADOS": gen_p, 
                                            "DÍAS GOZADOS": goz_p, 
                                            "SALDO": round(gen_p - goz_p, 2)
                                        })
                                        dias_generados_totales += gen_p
                                        curr_start = (pd.to_datetime(curr_start) + pd.DateOffset(years=1)).date()

                            # 3. Resumen Visual (Cuadros)
                            saldo_disponible = round(dias_generados_totales - dias_gozados_totales, 2)
                            st.markdown(f"""
                                <div style="display: flex; gap: 15px; margin-bottom: 20px;">
                                    <div style="flex: 1; background-color: #4A0000; padding: 15px; border-radius: 10px; text-align: center; border: 2px solid #FFD700;"><h2 style="color: #FFD700; margin: 0;">{dias_generados_totales:.2f}</h2><p style="color: white; margin: 0; font-size: 0.9em;">Días Generados</p></div>
                                    <div style="flex: 1; background-color: #4A0000; padding: 15px; border-radius: 10px; text-align: center; border: 2px solid #FFD700;"><h2 style="color: #FFD700; margin: 0;">{dias_gozados_totales:.2f}</h2><p style="color: white; margin: 0; font-size: 0.9em;">Días Gozados</p></div>
                                    <div style="flex: 1; background-color: #4A0000; padding: 15px; border-radius: 10px; text-align: center; border: 2px solid #FFD700;"><h2 style="color: #FFD700; margin: 0;">{saldo_disponible:.2f}</h2><p style="color: white; margin: 0; font-size: 0.9em;">Saldo Disponible</p></div>
                                </div>
                            """, unsafe_allow_html=True)

                            # 4. Desglose Amarillo (TABLA CALCULADA)
                            if detalles:
                                st.markdown("<h4 style='color: #FFD700;'>📅 Desglose Detallado por Periodos</h4>", unsafe_allow_html=True)
                                div_table = """<div style='border: 2px solid #FFD700; border-radius: 10px; overflow: hidden; margin-bottom: 20px;'>
                                    <table style='width: 100%; border-collapse: collapse; background-color: #FFF9C4; color: #4A0000;'>
                                        <tr style='background-color: #4A0000; color: #FFD700; font-weight: bold;'>
                                            <th style='padding: 10px;'>PERIODO</th><th>DEL / AL</th><th>GENERADOS</th><th>GOZADOS</th><th>SALDO</th>
                                        </tr>"""
                                for d in detalles:
                                    div_table += f"""<tr style='border-top: 1px solid #FFD700; text-align: center; font-weight: bold;'>
                                        <td style='padding: 8px;'>{d['PERIODO']}</td>
                                        <td><small>{d['DEL']} - {d['AL']}</small></td>
                                        <td>{d['DÍAS GENERADOS']:.2f}</td>
                                        <td style='color: #D32F2F;'>{d['DÍAS GOZADOS']:.2f}</td>
                                        <td style='background-color: #FFD700; color: black; padding: 5px;'>{d['SALDO']:.2f}</td>
                                    </tr>"""
                                div_table += "</table></div>"
                                st.markdown(div_table, unsafe_allow_html=True)

                            # 5. Editor de Datos (Historial de la Hoja)
                            vst = c_df.copy()
                            vst.columns = [str(c).upper().strip() for c in vst.columns]
                            if "SEL" not in vst.columns: vst.insert(0, "SEL", False)
                            
                            # Configuración de columnas
                            col_conf = {}
                            cols_ocultar = ["DNI", "APELLIDOS Y NOMBRES", "APELLIDOS", "NOMBRES", "DÍAS GENERADOS", "SALDO"]
                            for c in vst.columns:
                                if c in cols_ocultar: col_conf[c] = None
                                if "FECHA" in c or "F_" in c:
                                    vst[c] = pd.to_datetime(vst[c], errors='coerce').dt.date
                                    col_conf[c] = st.column_config.DateColumn(format="DD/MM/YYYY")

                            st.write("### Historial de Vacaciones (Registros)")
                            ed = st.data_editor(vst, hide_index=True, use_container_width=True, column_config=col_conf, key=f"ed_v_{dni_buscado}")
                            
                            # 6. Nuevo Registro y Papeleta
                            if not es_lector:
                                with st.expander("➕ Registrar Salida de Vacaciones"):
                                    # SE SOLUCIONA KEYERROR USANDO "PERIODO" EN MAYÚSCULAS
                                    opciones_p = [d["PERIODO"] for d in detalles] if detalles else ["S/P"]
                                    st.selectbox("Seleccione el Periodo", opciones_p, key=f"sel_p_v_{dni_buscado}")
                                    # ... resto de campos del formulario ...
                                    
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
                                                    d_area = ""  # Agregamos variable para AREA
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
                                                        
                                                        # Recuperamos el área del contrato anterior
                                                        v_area_old = str(last_c.get("area", ""))
                                                        d_area = "" if v_area_old.lower() == "nan" else v_area_old
                                                        
                                                        try: d_rem = float(last_c.get("remuneración básica", 0.0))
                                                        except: pass
                                                        d_bon = str(last_c.get("bonificación", ""))
                                                        d_cond = str(last_c.get("condición de trabajo", ""))
                                                        try: d_ini = pd.to_datetime(last_c["f_fin"]).date() + pd.Timedelta(days=1)
                                                        except: pass
                                                        
                                                        v_tt = str(last_c.get("tipo de trabajador", ""))
                                                        if v_tt in ["Administrativo", "Docente", "Externo"]: d_ttrab = v_tt
                                                        v_m = str(last_c.get("modalidad", ""))
                                                        if v_m in ["Presencial", "Semipresencial", "Virtual"]: d_mod = v_m
                                                        v_te = str(last_c.get("temporalidad", ""))
                                                        if v_te in ["Plazo fijo", "Plazo indeterminado", "Ordinarizado"]: d_temp = v_te
                                                        v_tc = str(last_c.get("tipo contrato", ""))
                                                        if v_tc in ["Planilla completo", "Tiempo Parcial", "Recibo por Honorarios", "Otro"]: d_tcont = v_tc

                                                    car = st.text_input("Cargo", value=d_car)
                                                    
                                                    # Input de AREA forzado a MAYÚSCULAS
                                                    area_input = st.text_input("AREA", value=d_area).upper() 
                                                    
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
                                                        
                                                        # --- SOLUCIÓN COLUMNAS DUPLICADAS ---
                                                        # Esto lee tus columnas reales de Google Sheets y las empareja automáticamente (ignora tildes y mayúsculas)
                                                        real_cols = {str(c).lower().replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').strip(): c for c in dfs[h_name].columns}
                                                        
                                                        new = {
                                                            real_cols.get("id", "id"): nid, 
                                                            real_cols.get("dni", "dni"): dni_buscado, 
                                                            real_cols.get("apellidos y nombres", "apellidos y nombres"): nom_c, 
                                                            real_cols.get("cargo", "cargo"): car, 
                                                            real_cols.get("area", "area"): area_input, 
                                                            real_cols.get("remuneracion basica", "remuneración básica"): rem_b, 
                                                            real_cols.get("bonificacion", "bonificación"): bono, 
                                                            real_cols.get("condicion de trabajo", "condición de trabajo"): cond, 
                                                            real_cols.get("f_inicio", "f_inicio"): ini, 
                                                            real_cols.get("f_fin", "f_fin"): fin, 
                                                            real_cols.get("tipo de trabajador", "tipo de trabajador"): t_trab, 
                                                            real_cols.get("modalidad", "modalidad"): mod, 
                                                            real_cols.get("temporalidad", "temporalidad"): temp, 
                                                            real_cols.get("link", "link"): lnk, 
                                                            real_cols.get("tipo contrato", "tipo contrato"): tcont, 
                                                            real_cols.get("estado", "estado"): est_a, 
                                                            real_cols.get("motivo cese", "motivo cese"): mot_a
                                                        }
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
                                    # TODO este bloque debe estar dentro del expander
                                    if not sel.empty:
                                        idx = sel.index[0]
                                        cols_reales = [c for c in vst.columns if c not in ["SEL"]]
                                        
                                        st.markdown("### 📝 Editar Registro")
                                        
                                        # Formulario de edición
                                        with st.form(key=f"form_edit_{h_name}_{dni_buscado}"):
                                            edit_row = {}
                                            for col in cols_reales:
                                                val = sel.iloc[0].get(col, "")
                                                
                                                # 1. Lógica para FECHAS
                                                if "fecha" in col.lower() or "f_" in col.lower():
                                                    try:
                                                        fecha_dt = pd.to_datetime(val, errors='coerce')
                                                        fecha_val = fecha_dt.date() if pd.notnull(fecha_dt) else date.today()
                                                    except:
                                                        fecha_val = date.today()
                                                        
                                                    edit_row[col] = st.date_input(
                                                        col.title(), 
                                                        value=fecha_val,
                                                        min_value=date(1930, 1, 1),
                                                        max_value=date(2100, 12, 31),
                                                        format="DD/MM/YYYY",
                                                        key=f"date_{h_name}_{col}_{dni_buscado}"
                                                    )
                                                
                                                # 2. Lógica para TEXTO O NÚMEROS (puedes añadir más elif aquí)
                                                else:
                                                    edit_row[col] = st.text_input(
                                                        col.title(),
                                                        value=str(val) if pd.notnull(val) else "",
                                                        key=f"edit_{h_name}_{col}_{dni_buscado}"
                                                    )

                                            # Botón de envío del formulario
                                            if st.form_submit_button("✅ Actualizar Registro"):
                                                for col in cols_reales:
                                                    dfs[h_name].at[idx, col.upper()] = edit_row[col]
                                                save_data(dfs)
                                                st.success("Registro actualizado")
                                                st.rerun()

                                        # Botón de eliminar (fuera del form pero dentro del expander)
                                        st.markdown("---")
                                        if st.button("🗑️ Eliminar Registro", type="primary", use_container_width=True, key=f"del_{h_name}_{dni_buscado}"):
                                            dfs[h_name] = dfs[h_name].drop(idx)
                                            save_data(dfs)
                                            st.rerun()
                                    
                                    else:
                                        st.info("💡 Selecciona la casilla **(SEL)** en la tabla para editar.")
                        
                        else:
                            st.info("💡 Activa la casilla (SEL) en la tabla superior para editar.")
                            edit_row = {}
                            for col in cols_reales:
                                val = sel.iloc[0].get(col, "")
                                
                                if "fecha" in col.lower() or "f_" in col.lower():
                                    edit_row[col] = st.date_input(
                                        col.title(), 
                                        value=pd.to_datetime(val, errors='coerce').date() if pd.notnull(pd.to_datetime(val, errors='coerce')) else date.today(), 
                                        min_value=date(1930, 1, 1), 
                                        max_value=date(2100, 12, 31), 
                                        format="DD/MM/YYYY",
                                        key=f"date_{h_name}_{col}_{dni_buscado}"
                                    )
                                elif col.lower() == "edad":
                                    fnac = edit_row.get("fecha de nacimiento")
                                    if fnac: 
                                        edad_calc = int(date.today().year - fnac.year - ((date.today().month, date.today().day) < (fnac.month, fnac.day)))
                                        edit_row[col] = st.number_input("Edad (Calculada)", value=edad_calc, disabled=True, key=f"edad_{h_name}_{dni_buscado}")
                                    else: 
                                        edit_row[col] = st.number_input(col.title(), value=int(val) if pd.notnull(val) and str(val).isdigit() else 0, disabled=True)
                                
                                elif col.lower() in ["remuneración", "bonificación", "sueldo", "días generados", "días gozados", "saldo", "monto"]:
                                    try: 
                                        num_val = float(val) if pd.notnull(val) else 0.0
                                    except: 
                                        num_val = 0.0
                                    edit_row[col] = st.number_input(col.title(), value=num_val, key=f"num_{h_name}_{col}_{dni_buscado}")
                                
                                else:
                                    edit_row[col] = st.text_input(
                                        col.title(), 
                                        value=str(val) if pd.notnull(val) else "", 
                                        key=f"edit_{h_name}_{col}_{dni_buscado}"
                                    )
                            
                            st.markdown("---")
                            # Botón de actualización dentro del formulario
                            if st.form_submit_button("✅ Actualizar Registro"):
                                for col in cols_reales:
                                    dfs[h_name].at[idx, col.upper()] = edit_row[col]
                                save_data(dfs)
                                st.success("¡Registro actualizado!")
                                st.rerun()

                        # --- BOTÓN DE ELIMINAR (FUERA DEL BUCLE DE COLUMNAS) ---
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("🗑️ Eliminar Registro Permanentemente", type="primary", use_container_width=True, key=f"del_{h_name}_{dni_buscado}"):
                            dfs[h_name] = dfs[h_name].drop(idx)
                            save_data(dfs)
                            st.rerun()

                    else: # Si no hay selección
                        st.info("💡 Selecciona la casilla **(SEL)** en la tabla para editar o eliminar datos.")
            else:
                st.error("DNI no encontrado.")
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
    # MÓDULO: VACACIONES (VERSIÓN ANTIDUPLICADOS)
    # ==========================================
    elif m == "Vacaciones":
        st.markdown("<h2 style='color: #4A0000;'>🌴 Reporte Integrado de Vacaciones</h2>", unsafe_allow_html=True)
        
        # 1. Carga de datos con RESET de índice y eliminación de columnas duplicadas
        d_p = dfs.get("PERSONAL", pd.DataFrame()).copy().reset_index(drop=True)
        d_v = dfs.get("VACACIONES", pd.DataFrame()).copy().reset_index(drop=True)
        d_c = dfs.get("CONTRATOS", pd.DataFrame()).copy().reset_index(drop=True)
        d_g = dfs.get("DATOS GENERALES", pd.DataFrame()).copy().reset_index(drop=True)

        if d_p.empty:
            st.warning("⚠️ No hay datos en la pestaña PERSONAL.")
        else:
            # LIMPIEZA DE COLUMNAS DUPLICADAS (Esto evita el ValueError)
            d_v = d_v.loc[:, ~d_v.columns.duplicated()]
            
            # Estandarizar nombres de columnas a minúsculas
            d_p.columns = [str(c).strip().lower() for c in d_p.columns]
            
            # Crear llave DNI
            col_dni_p = next((c for c in d_p.columns if "dni" in c), "dni")
            d_p["dni_key"] = d_p[col_dni_p].astype(str).str.strip().str.replace(".0", "", regex=False).str.zfill(8)
            
            # Nombre del trabajador
            col_nom_p = next((c for c in d_p.columns if "apellido" in c or "nombre" in c), "trabajador")
            
            # DataFrame Base
            res = d_p[["dni_key", col_nom_p]].copy()

            # 2. SEDE (Desde Datos Generales)
            if not d_g.empty:
                d_g = d_g.loc[:, ~d_g.columns.duplicated()]
                d_g.columns = [str(c).strip().lower() for c in d_g.columns]
                c_dni_g = next((c for c in d_g.columns if "dni" in c), None)
                if c_dni_g:
                    d_g["dni_key"] = d_g[c_dni_g].astype(str).str.strip().str.replace(".0", "", regex=False).str.zfill(8)
                    c_sede = next((c for c in d_g.columns if "sede" in c), None)
                    if c_sede:
                        df_sede = d_g[["dni_key", c_sede]].drop_duplicates("dni_key").rename(columns={c_sede: "Sede"})
                        res = res.merge(df_sede, on="dni_key", how="left")

            # 3. ÁREA (Desde Contratos)
            if not d_c.empty:
                d_c = d_c.loc[:, ~d_c.columns.duplicated()]
                d_c.columns = [str(c).strip().lower() for c in d_c.columns]
                c_dni_c = next((c for c in d_c.columns if "dni" in c), None)
                if c_dni_c:
                    d_c["dni_key"] = d_c[c_dni_c].astype(str).str.strip().str.replace(".0", "", regex=False).str.zfill(8)
                    c_area = next((c for c in d_c.columns if "area" in c or "rea" in c), None)
                    if c_area:
                        df_area = d_c.sort_index(ascending=False).drop_duplicates("dni_key")[["dni_key", c_area]].rename(columns={c_area: "Área"})
                        res = res.merge(df_area, on="dni_key", how="left")

            # 4. CÁLCULO DE DÍAS (Desde Vacaciones)
            if not d_v.empty:
                d_v.columns = [str(c).strip().lower() for c in d_v.columns]
                c_dni_v = next((c for c in d_v.columns if "dni" in c), None)
                c_dias_v = next((c for c in d_v.columns if "días" in c or "dias" in c), None)

                if c_dni_v and c_dias_v:
                    # Reset index de nuevo por seguridad antes de crear columnas
                    d_v = d_v.reset_index(drop=True)
                    d_v["dni_key"] = d_v[c_dni_v].astype(str).str.strip().str.replace(".0", "", regex=False).str.zfill(8)
                    
                    # Conversión numérica segura
                    def a_numero(x):
                        try:
                            if pd.isna(x): return 0.0
                            return float(str(x).replace(",", ".").strip())
                        except:
                            return 0.0
                    
                    # Usamos una serie temporal para evitar problemas de reindexación
                    valores_num = [a_numero(v) for v in d_v[c_dias_v]]
                    d_v["num"] = valores_num
                    
                    d_sum = d_v.groupby("dni_key")["num"].sum().reset_index().rename(columns={"num": "Días"})
                    res = res.merge(d_sum, on="dni_key", how="left")

            # 5. LIMPIEZA FINAL
            res["Sede"] = res.get("Sede", pd.Series(dtype='object')).fillna("No registrada")
            res["Área"] = res.get("Área", pd.Series(dtype='object')).fillna("No registrada")
            res["Días"] = res.get("Días", pd.Series(dtype='float')).fillna(0.0)
            
            res.rename(columns={"dni_key": "DNI", col_nom_p: "Trabajador"}, inplace=True)

            # 6. FILTROS E INTERFAZ
            st.markdown("### 🔍 Filtros")
            col1, col2 = st.columns(2)
            with col1:
                s_op = ["Todas"] + sorted(res["Sede"].unique().astype(str).tolist())
                f_sede = st.selectbox("Sede", s_op)
            with col2:
                a_op = ["Todas"] + sorted(res["Área"].unique().astype(str).tolist())
                f_area = st.selectbox("Área", a_op)

            # Aplicar filtros
            final = res.copy()
            if f_sede != "Todas": final = final[final["Sede"] == f_sede]
            if f_area != "Todas": final = final[final["Área"] == f_area]

            # 7. TABLA
            st.info(f"Registros mostrados: {len(final)}")
            st.dataframe(
                final[["DNI", "Trabajador", "Sede", "Área", "Días"]].style.format({"Días": "{:.2f}"}),
                hide_index=True,
                use_container_width=True
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

# ==========================================
    # MÓDULO: VACACIONES (VERSIÓN DEFINITIVA)
    # ==========================================
    elif m == "Vacaciones":
        st.markdown("<h2 style='color: #4A0000;'>🌴 Reporte Integrado de Vacaciones</h2>", unsafe_allow_html=True)
        
        # 1. Carga de datos con limpieza de índices
        d_p = dfs.get("PERSONAL", pd.DataFrame()).copy().reset_index(drop=True)
        d_v = dfs.get("VACACIONES", pd.DataFrame()).copy().reset_index(drop=True)
        d_c = dfs.get("CONTRATOS", pd.DataFrame()).copy().reset_index(drop=True)
        d_g = dfs.get("DATOS GENERALES", pd.DataFrame()).copy().reset_index(drop=True)

        if d_p.empty:
            st.warning("⚠️ No hay datos en la pestaña PERSONAL.")
        else:
            # Estandarizar nombres de columnas a minúsculas
            d_p.columns = [str(c).strip().lower() for c in d_p.columns]
            
            # Crear llave DNI
            col_dni_p = next((c for c in d_p.columns if "dni" in c), "dni")
            d_p["dni_key"] = d_p[col_dni_p].astype(str).str.strip().str.replace(".0", "", regex=False).str.zfill(8)
            
            # Nombre del trabajador
            col_nom_p = next((c for c in d_p.columns if "apellido" in c or "nombre" in c), "trabajador")
            
            # DataFrame Base
            res = d_p[["dni_key", col_nom_p]].copy()

            # 2. SEDE (Desde Datos Generales)
            if not d_g.empty:
                d_g.columns = [str(c).strip().lower() for c in d_g.columns]
                c_dni_g = next((c for c in d_g.columns if "dni" in c), None)
                if c_dni_g:
                    d_g["dni_key"] = d_g[c_dni_g].astype(str).str.strip().str.replace(".0", "", regex=False).str.zfill(8)
                    c_sede = next((c for c in d_g.columns if "sede" in c), None)
                    if c_sede:
                        df_sede = d_g[["dni_key", c_sede]].drop_duplicates("dni_key").rename(columns={c_sede: "Sede"})
                        res = res.merge(df_sede, on="dni_key", how="left")

            # 3. ÁREA (Desde Contratos)
            if not d_c.empty:
                d_c.columns = [str(c).strip().lower() for c in d_c.columns]
                c_dni_c = next((c for c in d_c.columns if "dni" in c), None)
                if c_dni_c:
                    d_c["dni_key"] = d_c[c_dni_c].astype(str).str.strip().str.replace(".0", "", regex=False).str.zfill(8)
                    c_area = next((c for c in d_c.columns if "area" in c or "rea" in c), None)
                    if c_area:
                        df_area = d_c.sort_index(ascending=False).drop_duplicates("dni_key")[["dni_key", c_area]].rename(columns={c_area: "Área"})
                        res = res.merge(df_area, on="dni_key", how="left")

            # 4. CÁLCULO DE DÍAS (Desde Vacaciones)
            if not d_v.empty:
                d_v.columns = [str(c).strip().lower() for c in d_v.columns]
                c_dni_v = next((c for c in d_v.columns if "dni" in c), None)
                c_dias_v = next((c for c in d_v.columns if "días" in c or "dias" in c), None)

                if c_dni_v and c_dias_v:
                    d_v["dni_key"] = d_v[c_dni_v].astype(str).str.strip().str.replace(".0", "", regex=False).str.zfill(8)
                    
                    # Conversión numérica segura
                    def a_numero(x):
                        try:
                            return float(str(x).replace(",", ".").strip()) if x else 0.0
                        except:
                            return 0.0
                    
                    d_v["num"] = d_v[c_dias_v].apply(a_numero)
                    d_sum = d_v.groupby("dni_key")["num"].sum().reset_index().rename(columns={"num": "Días"})
                    res = res.merge(d_sum, on="dni_key", how="left")

            # 5. LIMPIEZA FINAL
            res["Sede"] = res.get("Sede", pd.Series(dtype='object')).fillna("No registrada")
            res["Área"] = res.get("Área", pd.Series(dtype='object')).fillna("No registrada")
            res["Días"] = res.get("Días", pd.Series(dtype='float')).fillna(0.0)
            
            res.rename(columns={"dni_key": "DNI", col_nom_p: "Trabajador"}, inplace=True)

            # 6. FILTROS E INTERFAZ
            st.markdown("### 🔍 Filtros")
            col1, col2 = st.columns(2)
            with col1:
                s_op = ["Todas"] + sorted(res["Sede"].unique().astype(str).tolist())
                f_sede = st.selectbox("Sede", s_op)
            with col2:
                a_op = ["Todas"] + sorted(res["Área"].unique().astype(str).tolist())
                f_area = st.selectbox("Área", a_op)

            # Aplicar filtros
            final = res.copy()
            if f_sede != "Todas": final = final[final["Sede"] == f_sede]
            if f_area != "Todas": final = final[final["Área"] == f_area]

            # 7. TABLA
            st.info(f"Registros: {len(final)}")
            st.dataframe(
                final[["DNI", "Trabajador", "Sede", "Área", "Días"]].style.format({"Días": "{:.2f}"}),
                hide_index=True,
                use_container_width=True
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

































































































































































































































































































































