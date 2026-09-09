# -*- coding: utf-8 -*-
import json
import os
import sys
import time
from datetime import date, datetime
from io import BytesIO

# --- LIBRERÍAS EXTERNAS ---
from google.oauth2.service_account import Credentials
import gspread
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont, ImageOps
import requests
import streamlit as st
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt

# Garantizar el path raíz de la aplicación
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Gestión Roosevelt", page_icon="🎓", layout="wide"
)

# --- IMPORTS DE MÓDULOS DEL SISTEMA ---
import estructura as mod_estructura
import gestor_evaluaciones as mod_gestor_evaluaciones
import mod_editor
import mod_horarios_admin as mod_horarios_admin
import mod_nomina
import mod_procesador_asistencia as mod_procesador_asistencia
import mod_registro
import mod_reportes as mod_dashboard
import mod_usuarios
import repcumpleanos as mod_cumpleanos
import reportegeneral as mod_reportegeneral
import repvacaciones as mod_vacaciones
import repvencimientos as mod_vencimientos

# --- IMPORTACIÓN DE MÓDULO BASE DE DATOS (GOOGLE SHEETS) ---
from mod_guardar_sheets import cargar_df_desde_sheets, exportar_df_a_sheets

# ==========================================
# 1. CONFIGURACIÓN Y CONSTANTES
# ==========================================
SHEET_NAME = "DB_SISTEMA_GTH"
F_N = "MG. ARTURO JAVIER GALINDO MARTINEZ"
F_C = "JEFE DE GESTIÓN DEL TALENTO HUMANO"

MOTIVOS_CESE = [
    "Término de contrato",
    "Renuncia",
    "Despido",
    "Mutuo acuerdo",
    "Fallecimiento",
    "Otros",
]

COLUMNAS = {
    "PERSONAL": ["dni", "apellidos y nombres", "link"],
    "DATOS GENERALES": [
        "dni",
        "sede",
        "sexo",
        "apellidos y nombres",
        "dirección",
        "estado civil",
        "fecha de nacimiento",
        "edad",
    ],
    "DATOS FAMILIARES": [
        "parentesco",
        "apellidos y nombres",
        "dni",
        "fecha de nacimiento",
        "edad",
        "estudios",
        "telefono",
    ],
    "EXP. LABORAL": [
        "dni",
        "tipo de experiencia",
        "lugar",
        "puesto",
        "fecha de inicio",
        "fecha de fin",
        "motivo de cese",
    ],
    "FORM. ACADEMICA": [
        "dni",
        "tipo de estudio",
        "institución educativa",
        "mención (especialidad / carrera / etc)",
        "año",
        "estado",
        "horas académicas",
        "grado o título obtenido",
    ],
    "INVESTIGACION": [
        "id",
        "dni",
        "tipo de registro",
        "enlace cti vitae",
        "codigo renacyt",
        "nivel renacyt",
        "titulo de publicacion",
        "base de datos",
        "nombre de revista",
        "cuartil",
        "año de publicacion",
        "doi o url",
        "nombre del proyecto",
        "entidad financiadora",
        "rol en el proyecto",
        "monto adjudicado",
        "estado del proyecto",
        "nombre del semillero",
        "resolucion",
        "rol en el semillero",
        "estado del semillero",
    ],
    "CONTRATOS": [
        "dni",
        "cargo",
        "AREA",
        "f_inicio",
        "f_fin",
        "tipo de trabajador",
        "modalidad",
        "temporalidad",
        "tipo contrato",
        "estado",
        "LINK",
    ],
    "VACACIONES": [
        "periodo",
        "fecha de inicio",
        "fecha de fin",
        "días generados",
        "dias gozados",
        "saldo",
        "link",
    ],
    "OTROS BENEFICIOS": ["periodo", "tipo de beneficio", "link"],
    "MERITOS Y DEMERITOS": ["periodo", "merito o demerito", "motivo", "link"],
    "EVALUACION DEL DESEMPEÑO": [
        "periodo",
        "merito o demerito",
        "motivo",
        "link",
    ],
    "LIQUIDACIONES": ["periodo", "firmo", "link"],
}

def obtener_link_directo_drive(url):
    """Convierte un link de compartir de Google Drive en un link directo de imagen."""
    if not isinstance(url, str) or not url.strip():
        return None
    if "drive.google.com" in url and "/d/" in url:
        try:
            file_id = url.split("/d/")[1].split("/")[0]
            return f"https://drive.google.com/uc?export=view&id={file_id}"
        except Exception:
            return url
    return url

# ==========================================
# 2. FUNCIONES DE DATOS (VERSIÓN ACTUALIZADA)
# ==========================================

SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def obtener_credenciales():
    """Autentica con Google APIs sin usar libraries obsoletas."""
    if "gcp_service_account" in st.secrets:
        return Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]), scopes=SCOPE
        )
    elif "google_json" in st.secrets:
        creds_dict = json.loads(st.secrets["google_json"])
        return Credentials.from_service_account_info(
            creds_dict, scopes=SCOPE
        )
    else:
        return Credentials.from_service_account_file(
            "credenciales.json", scopes=SCOPE
        )

@st.cache_data(ttl=240)
def load_data():
    creds = obtener_credenciales()
    client = gspread.authorize(creds)
    spreadsheet = client.open(SHEET_NAME)
    worksheets = spreadsheet.worksheets()

    dfs = {}
    for worksheet in worksheets:
        try:
            time.sleep(0.6)

            data = worksheet.get_all_records()
            df = pd.DataFrame(data)
            if not df.empty:
                df.columns = [
                    str(c)
                    .strip()
                    .lower()
                    .replace("á", "a")
                    .replace("é", "e")
                    .replace("í", "i")
                    .replace("ó", "o")
                    .replace("ú", "u")
                    .replace("_", " ")
                    for c in df.columns
                ]

                df = df.loc[:, ~df.columns.duplicated()].copy()

                if worksheet.title == "CONTRATOS":
                    for col in df.columns:
                        if "inicio" in col:
                            df.rename(columns={col: "f_inicio"}, inplace=True)
                        if "termino" in col or "fin" in col:
                            df.rename(columns={col: "f_fin"}, inplace=True)

                if "dni" in df.columns:
                    df["dni"] = (
                        df["dni"]
                        .astype(str)
                        .str.strip()
                        .str.replace(r"\.0$", "", regex=True)
                        .str.zfill(8)
                    )

                col_fecha = next(
                    (
                        c
                        for c in df.columns
                        if "fecha de nacimiento" in c or "fecha nacimiento" in c
                    ),
                    None,
                )

                if col_fecha:
                    def calcular_edad_viva(fecha_str):
                        if (
                            pd.isna(fecha_str)
                            or str(fecha_str).strip() == ""
                        ):
                            return 0
                        try:
                            if isinstance(fecha_str, str):
                                fnac_date = pd.to_datetime(
                                    fecha_str, dayfirst=True
                                ).date()
                            else:
                                fnac_date = (
                                    fecha_str.date()
                                    if hasattr(fecha_str, "date")
                                    else fecha_str
                                )

                            hoy = date.today()
                            return (
                                hoy.year
                                - fnac_date.year
                                - (
                                    (hoy.month, hoy.day)
                                    < (fnac_date.month, fnac_date.day)
                                )
                            )
                        except Exception:
                            return 0

                    df["edad"] = df[col_fecha].apply(calcular_edad_viva)

                dfs[worksheet.title] = df
            else:
                dfs[worksheet.title] = pd.DataFrame()
        except Exception as e:
            st.error(f"Error en {worksheet.title}: {e}")
            dfs[worksheet.title] = pd.DataFrame()
            time.sleep(2)

    return dfs

def save_data(dfs, pestana_especifica=None):
    creds = obtener_credenciales()
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME)

    listado_pestanas = (
        [pestana_especifica] if pestana_especifica else dfs.keys()
    )

    for h in listado_pestanas:
        if h not in dfs:
            continue

        df = dfs[h]
        if df.empty or len(df.columns) == 0:
            continue

        worksheet = sheet.worksheet(h)
        df_s = df.copy()

        df_s = df_s.loc[:, ~df_s.columns.duplicated()]
        df_s = df_s.fillna("")
        df_s = df_s.astype(str)

        fantasmas = ["nan", "NaN", "NaT", "nat", "None", "<NA>"]
        for fantasma in fantasmas:
            df_s = df_s.replace(fantasma, "")

        df_s.columns = [str(c).upper() for c in df_s.columns]

        if not pestana_especifica:
            time.sleep(0.6)

        worksheet.clear()
        datos_a_guardar = (
            [df_s.columns.values.tolist()] + df_s.values.tolist()
        )
        worksheet.update(datos_a_guardar)

    st.cache_data.clear()

def get_consolidated_contracts(df_c):
    if df_c.empty:
        return df_c
    df_c = df_c.copy()
    df_c["f_inicio"] = pd.to_datetime(df_c["f_inicio"], errors="coerce")
    df_c["f_fin"] = pd.to_datetime(df_c["f_fin"], errors="coerce")
    df_c = df_c.sort_values("f_inicio").dropna(subset=["f_inicio"])

    merged = []
    for _, row in df_c.iterrows():
        if not merged:
            merged.append(row.to_dict())
        else:
            last = merged[-1]
            if pd.notnull(last["f_fin"]) and row[
                "f_inicio"
            ] <= last["f_fin"] + pd.Timedelta(days=1):
                last["f_fin"] = (
                    max(last["f_fin"], row["f_fin"])
                    if pd.notnull(row["f_fin"])
                    else row["f_fin"]
                )
                last["cargo"] = row["cargo"]
            else:
                merged.append(row.to_dict())
    return pd.DataFrame(merged)

def gen_word(
    nom, dni, df_c, tipo_seleccionado="Automático (Detectar por historial)"
):
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

    es_docente = False
    es_locacion = False
    tipo_upper = tipo_seleccionado.upper()

    if "AUTOM" in tipo_upper:
        if not df_c.empty:
            texto_historial = " ".join(
                df_c.astype(str).agg(" ".join, axis=1).str.lower().tolist()
            )
            if "docente" in texto_historial or "catedra" in texto_historial:
                es_docente = True
            if "honorario" in texto_historial or "locaci" in texto_historial:
                es_locacion = True
    else:
        if "DOCENTE" in tipo_upper:
            es_docente = True
        if (
            "LOCACI" in tipo_upper
            or "SERVICIO" in tipo_upper
            or "HONORARIO" in tipo_upper
        ):
            es_locacion = True

    filas_texto = df_c.astype(str).agg(" ".join, axis=1).str.lower()
    mask_locacion = filas_texto.str.contains(
        "honorario|locaci|tercero", na=False
    )

    if es_locacion:
        df_c_filtrado = df_c[mask_locacion]
    else:
        df_c_filtrado = df_c[~mask_locacion]

    df_merged = get_consolidated_contracts(df_c_filtrado)
    df_tabla = df_merged

    titulo_certificado = "CERTIFICADO DE TRABAJO"
    texto_introduccion = "La oficina de Gestión de Talento Humano De La Universidad Privada De Huancayo “Franklin Roosevelt”, certifica que:"
    texto_cuerpo_identificacion = ""
    columna_tabla_cargo = "CARGO / FUNCIÓN"

    if not es_docente and not es_locacion:
        titulo_certificado = "CERTIFICADO DE TRABAJO"
        texto_cuerpo_identificacion = f"El(la) ex-servidor(a) administrativo(a) {nom.upper()}, identificado(a) con DNI N° {dni}, ha laborado en nuestra institución bajo el régimen laboral de la actividad privada, desempeñando funciones de manera subordinada de acuerdo al siguiente detalle:"

    elif not es_docente and es_locacion:
        titulo_certificado = "CONSTANCIA DE PRESTACIÓN DE SERVICIOS"
        texto_introduccion = "La oficina de Gestión de Talento Humano De La Universidad Privada De Huancayo “Franklin Roosevelt”, hace constar que:"
        texto_cuerpo_identificacion = f"El(la) señor(a) {nom.upper()}, identificado(a) con DNI N° {dni}, ha prestado servicios autónomos e independientes de naturaleza civil bajo la modalidad de Locación de Servicios, realizando actividades de índole administrativa según el siguiente detalle:"
        columna_tabla_cargo = "ACTIVIDAD / SERVICIO"

    elif es_docente and not es_locacion:
        titulo_certificado = "CERTIFICADO DE TRABAJO"
        texto_cuerpo_identificacion = f"El(la) docente {nom.upper()}, identificado(a) con DNI N° {dni}, ha laborado en nuestra casa de estudios superiores ejerciendo funciones pedagógicas y de cátedra universitaria, bajo el régimen laboral correspondiente, de acuerdo al siguiente detalle:"

    elif es_docente and es_locacion:
        titulo_certificado = "CONSTANCIA DE LOCACIÓN DE SERVICIOS DOCENTES"
        texto_introduccion = "La oficina de Gestión de Talento Humano De La Universidad Privada De Huancayo “Franklin Roosevelt”, hace constar que:"
        texto_cuerpo_identificacion = f"El(la) profesional {nom.upper()}, identificado(a) con DNI N° {dni}, ha prestado servicios profesionales independientes de docencia universitaria bajo el régimen civil de Locación de Servicios, dictando asignaturas académicas de acuerdo al siguiente detalle:"
        columna_tabla_cargo = "CÁTEDRA / ASIGNATURA"

    p_tit = doc.add_paragraph()
    p_tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_tit = p_tit.add_run(titulo_certificado)
    r_tit.bold, r_tit.font.name, r_tit.font.size = True, "Arial", Pt(18)

    p_intro = doc.add_paragraph(f"\n{texto_introduccion}")
    p_intro.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_intro.paragraph_format.line_spacing = 1.15

    p_inf = doc.add_paragraph()
    p_inf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_inf.paragraph_format.line_spacing = 1.15
    p_inf.add_run(texto_cuerpo_identificacion)

    t = doc.add_table(rows=1, cols=3)
    t.style = "Table Grid"

    for i, h in enumerate([columna_tabla_cargo, "FECHA INICIO", "FECHA FIN"]):
        celda = t.rows[0].cells[i]
        celda.text = h
        celda.paragraphs[0].runs[0].font.bold = True
        celda.paragraphs[0].runs[0].font.name = "Arial"

    for _, fila in df_tabla.iterrows():
        celdas = t.add_row().cells
        celdas[0].text = str(
            fila.get("cargo", fila.get("puesto", ""))
        ).upper()
        celdas[1].text = (
            pd.to_datetime(fila["f_inicio"]).strftime("%d/%m/%Y")
            if pd.notnull(fila["f_inicio"])
            else ""
        )
        celdas[2].text = (
            pd.to_datetime(fila["f_fin"]).strftime("%d/%m/%Y")
            if pd.notnull(fila["f_fin"])
            else "EN LA ACTUALIDAD"
        )

        for celda in celdas:
            if celda.paragraphs[0].runs:
                celda.paragraphs[0].runs[0].font.name = "Arial"
                celda.paragraphs[0].runs[0].font.size = Pt(10)

    p_cierre = doc.add_paragraph(
        "\nSe expide el presente a solicitud del interesado para los fines que considere convenientes."
    )
    p_cierre.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    p_fecha = doc.add_paragraph(
        f"\nHuancayo, {date.today().strftime('%d/%m/%Y')}"
    )
    p_fecha.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_fecha.runs[0].font.name = "Arial"

    f = doc.add_paragraph()
    f.alignment = WD_ALIGN_PARAGRAPH.CENTER
    f_run = f.add_run("\n\n__________________________\n" + F_N + "\n" + F_C)
    f_run.bold = True
    f_run.font.name = "Arial"

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


def gen_papeleta_vac(
    apellidos,
    nombres,
    dni_b,
    position,
    f_ingreso,
    period,
    start_d,
    end_d,
    days,
):
    template_path = "Template_Papeleta.docx"

    if not os.path.exists(template_path):
        st.error(
            f"⚠️ No se encontró la plantilla en: {template_path}. Por favor crea el archivo Word."
        )
        return None

    doc = Document(template_path)

    hoy = date.today()
    meses = [
        "enero",
        "febrero",
        "marzo",
        "abril",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre",
    ]
    txt_firma = (
        f"Huancayo, {hoy.day} de {meses[hoy.month-1]} de {hoy.year}"
    )

    fin_dt = pd.to_datetime(end_d, errors="coerce")
    if pd.notnull(fin_dt):
        retorno_dt = fin_dt + pd.Timedelta(days=1)
        if retorno_dt.weekday() == 6:
            retorno_dt += pd.Timedelta(days=1)
        str_retorno = retorno_dt.strftime("%d/%m/%Y")
    else:
        str_retorno = ""

    replacements = {
        "{{APELLIDOS}}": str(apellidos).upper(),
        "{{NOMBRES}}": str(nombres).upper(),
        "{{DNI}}": str(dni_b),
        "{{CARGO}}": str(position).upper(),
        "{{F_INGRESO}}": (
            f_ingreso.strftime("%d/%m/%Y")
            if isinstance(f_ingreso, (date, datetime))
            else str(f_ingreso)
        ),
        "{{PERIODO}}": str(period),
        "{{F_INICIO}}": (
            start_d.strftime("%d/%m/%Y")
            if isinstance(start_d, (date, datetime))
            else str(start_d)
        ),
        "{{F_FIN}}": (
            end_d.strftime("%d/%m/%Y")
            if isinstance(end_d, (date, datetime))
            else str(end_d)
        ),
        "{{F_RETORNO}}": str_retorno,
        "{{DIAS}}": str(days),
        "{{FECHA_FIRMA}}": txt_firma,
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
st.markdown(
    """
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
    
    /* BOTONES CON MEJOR CONTRASTE */
    div.stButton > button, [data-testid="stFormSubmitButton"] > button { 
        background-color: #FFD700 !important; 
        border: 2px solid #4a0000 !important; 
        border-radius: 10px !important; 
    }

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

    /* FONDOS Y CAJAS DE TEXTO */
    [data-testid="stExpander"] { 
        background-color: #FFF9C4 !important; 
        border: 2px solid #FFD700 !important; 
        border-radius: 10px !important; 
    }
    
    [data-testid="stExpander"] details { background-color: transparent !important; }
    [data-testid="stExpander"] summary { background-color: #FFD700 !important; padding: 10px !important; border-radius: 8px 8px 0 0 !important; }
    [data-testid="stExpander"] summary p { color: #4a0000 !important; font-weight: bold !important; font-size: 16px !important; }

    [data-baseweb="input"], [data-baseweb="select"], [data-baseweb="textarea"] { 
        background-color: #FFFFFF !important; 
        border: 1px solid #4a0000 !important; 
        border-radius: 5px !important; 
    }
    
    .stApp input, .stApp select, .stApp textarea, [data-baseweb="select"] span { 
        color: #000000 !important; 
        font-weight: bold !important; 
        -webkit-text-fill-color: #000000 !important;
    }

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

    /* TABLAS INTERACTIVAS */
    [data-testid="stDataEditor"], [data-testid="stTable"], .stTable { background-color: white !important; border-radius: 10px !important; overflow: hidden !important; }
    
    [data-testid="stDataEditor"] .react-grid-HeaderCell span { 
        color: #000000 !important; 
        font-weight: 900 !important; 
        font-size: 15px !important; 
        text-transform: uppercase !important; 
    }
    
    thead tr th { background-color: #FFF9C4 !important; color: #000000 !important; font-weight: bold !important; text-transform: uppercase !important; border: 1px solid #f0f0f0 !important; }
    
    /* SUBTÍTULOS (LABELS DE LOS FORMULARIOS) */
    label p, label span, .stApp label p { 
        color: #FFD700 !important; 
        font-weight: bold !important; 
        font-size: 16px !important; 
    }
    
    [data-testid="stExpander"] label p, [data-testid="stExpander"] label span { 
        color: #4a0000 !important; 
        font-weight: bold !important; 
    }
</style>
""",
    unsafe_allow_html=True,
)

# ==========================================
# 4. LÓGICA DE DATOS Y SESIÓN
# ==========================================
if "rol" not in st.session_state:
    st.session_state.rol = None
if "usuario_actual" not in st.session_state:
    st.session_state.usuario_actual = None

# ---> CARGAMOS LOS DATOS ANTES DEL LOGIN <---
dfs = load_data()

if st.session_state.rol is None:
    st.markdown(
        "<h3 style='text-align: center; color: #FFD700;'>¡Tu talento es importante! :)</h3>",
        unsafe_allow_html=True,
    )

    col_logo1, col_logo2, col_logo3 = st.columns([1, 1.2, 1])
    with col_logo2:
        if os.path.exists("Logo_amarillo.png"):
            st.image("Logo_amarillo.png", use_container_width=True)

    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        u = st.text_input("USUARIO").lower().strip()
        p = st.text_input("CONTRASEÑA", type="password")
        st.markdown(
            '<p style="color:white; text-align:center; font-weight:bold; margin-top:15px;">Bienvenido (a) al sistema de gestión de datos de los colaboradores</p>',
            unsafe_allow_html=True,
        )

        if st.button("INGRESAR"):
            df_usuarios = dfs.get("USUARIOS", pd.DataFrame())

            if not df_usuarios.empty and "usuario" in df_usuarios.columns:
                user_match = df_usuarios[
                    (df_usuarios["usuario"].astype(str).str.lower() == u)
                    & (df_usuarios["password"].astype(str) == p)
                ]

                if not user_match.empty:
                    estado = (
                        str(user_match.iloc[0].get("estado", "Activo"))
                        .title()
                        .strip()
                    )
                    if estado == "Inactivo":
                        st.error(
                            "⚠️ Tu cuenta está inactiva. Contacta al administrador."
                        )
                    else:
                        st.session_state.rol = (
                            user_match.iloc[0]
                            .get("rol", "Lector")
                            .strip()
                            .capitalize()
                        )
                        st.session_state.usuario_actual = u
                        st.rerun()
                else:
                    if u == "admin" and p == "12345":
                        st.session_state.rol = "Admin"
                        st.session_state.usuario_actual = "admin"
                        st.rerun()
                    else:
                        st.error("❌ Credenciales incorrectas.")
            else:
                if u == "admin" and p == "12345":
                    st.session_state.rol = "Admin"
                    st.session_state.usuario_actual = "admin"
                    st.rerun()
                else:
                    st.error("❌ No hay base de usuarios. Usa admin / 12345.")

else:
    es_lector = st.session_state.rol == "Lector"

    with st.sidebar:
        st.markdown("<br>", unsafe_allow_html=True)
        col_logo_1, col_logo_2, col_logo_3 = st.columns([1, 2, 1])
        with col_logo_2:
            if os.path.exists("Logo_guindo.png"):
                st.image("Logo_guindo.png", use_container_width=True)
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown(
            f"<div style='text-align: center; color:#FFD700;'>Hola, <b>{st.session_state.usuario_actual}</b><br><small>Rol: {st.session_state.rol}</small></div>",
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)

        if "menu_p" not in st.session_state:
            st.session_state.menu_p = "🔍 Consulta"
        if "menu_r" not in st.session_state:
            st.session_state.menu_r = None
        if "menu_activo" not in st.session_state:
            st.session_state.menu_activo = "🔍 Consulta"

        def click_menu_p():
            st.session_state.menu_activo = st.session_state.menu_p
            st.session_state.menu_r = None

        def click_menu_r():
            if st.session_state.menu_r is not None:
                st.session_state.menu_activo = st.session_state.menu_r
                st.session_state.menu_p = None

        st.markdown("### 🛠️ MENÚ PRINCIPAL")
        st.radio(
            "Menú Principal",
            [
                "🔍 Consulta",
                "➕ Registro",
                "⏰ Horarios Administrativos",
                "📊 Nómina General",
                "🏢 Estructura",
                "📋 Evaluaciones",
                "📈 Dashboard Desempeño",
            ],
            key="menu_p",
            on_change=click_menu_p,
            index=None,
            label_visibility="collapsed",
        )

        st.markdown(
            "<h3 style='color: #FFD700;'>📊 REPORTES</h3>",
            unsafe_allow_html=True,
        )
        st.radio(
            "Reportes",
            ["Reporte General", "Cumpleañeros", "Vacaciones", "Vencimientos"],
            key="menu_r",
            on_change=click_menu_r,
            index=None,
            label_visibility="collapsed",
        )

        def click_usuarios():
            st.session_state.menu_activo = "🔐 Usuarios y Seguridad"
            st.session_state.menu_p = None
            st.session_state.menu_r = None

        st.markdown("---")
        st.button(
            "🔐 Usuarios y Seguridad",
            use_container_width=True,
            on_click=click_usuarios,
        )

        m = st.session_state.menu_activo

        st.markdown("---")
        if st.button("🚪 Cerrar Sesión", key="btn_logout"):
            st.session_state.rol = None
            st.session_state.usuario_actual = None
            st.session_state.menu_activo = "🔍 Consulta"
            st.rerun()

    # === SECCIÓN DE MÓDULOS ===
    if m == "🔍 Consulta":
        st.markdown(
            "<h2 style='color: #FFD700;'>Búsqueda de Colaborador</h2>",
            unsafe_allow_html=True,
        )

        df_per_consulta = dfs["PERSONAL"].copy()

        df_per_consulta["dni_str"] = (
            df_per_consulta.get("dni", pd.Series([""] * len(df_per_consulta)))
            .astype(str)
            .str.strip()
        )
        apellidos_col = (
            df_per_consulta.get(
                "apellidos", pd.Series([""] * len(df_per_consulta))
            )
            .fillna("")
            .astype(str)
            .str.strip()
        )
        nombres_col = (
            df_per_consulta.get(
                "nombres", pd.Series([""] * len(df_per_consulta))
            )
            .fillna("")
            .astype(str)
            .str.strip()
        )

        df_per_consulta["nom_str"] = (
            apellidos_col + " " + nombres_col
        ).str.strip()
        df_per_consulta["search_str"] = (
            df_per_consulta["dni_str"] + " - " + df_per_consulta["nom_str"]
        )

        opciones_buscador = [""] + [
            x
            for x in df_per_consulta["search_str"].tolist()
            if x != " - "
        ]

        selected_search = st.selectbox(
            "🔍 Escriba el DNI o Apellidos y Nombres:", opciones_buscador
        )

        if selected_search:
            dni_buscado = selected_search.split(" - ")[0].strip()

            fila_pers = df_per_consulta[
                df_per_consulta["dni_str"] == dni_buscado
            ]
            if not fila_pers.empty:
                nom_c = fila_pers.iloc[0]["nom_str"]
                ape_c = str(fila_pers.iloc[0].get("apellidos", "")).strip()
                nom_p_c = str(fila_pers.iloc[0].get("nombres", "")).strip()

                link_foto_raw = fila_pers.iloc[0].get(
                    "foto", fila_pers.iloc[0].get("FOTO", "")
                )

                if pd.notnull(link_foto_raw) and str(link_foto_raw).strip() != "":
                    foto_directa = obtener_link_directo_drive(
                        str(link_foto_raw).strip()
                    )
                else:
                    foto_directa = None

                if foto_directa:
                    st.markdown(
                        f"""
                        <style>
                        .foto-perfil-large {{
                            width: 110px;
                            height: 110px;
                            border-radius: 50%; 
                            object-fit: cover; 
                            object-position: center;
                            border: 4px solid #FFD700;
                            margin-right: 20px;
                            box-shadow: 0 4px 10px rgba(0,0,0,0.3);
                            transition: transform 0.2s ease-in-out;
                        }}
                        .foto-perfil-large:hover {{
                            transform: scale(1.08);
                        }}
                        </style>
                        <div style='border-bottom: 2px solid #FFD700; padding-bottom: 15px; margin-bottom: 25px; display: flex; align-items: center;'>
                            <img src='{foto_directa}' class='foto-perfil-large' onerror="this.style.display='none'; document.getElementById('avatar-{dni_buscado}').style.display='block';">
                            <h1 id='avatar-{dni_buscado}' style='color: white; margin: 0; margin-right: 15px; font-size: 3em; display: none;'>👤</h1>
                            <h1 style='color: #FFD700; margin: 0; font-size: 2.5em;'>{nom_c}</h1>
                        </div>
                    """,
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f"""
                        <div style='border-bottom: 2px solid #FFD700; padding-bottom: 10px; margin-bottom: 20px; display: flex; align-items: center;'>
                            <h1 style='color: white; margin: 0; margin-right: 15px; font-size: 3em;'>👤</h1>
                            <h1 style='color: #FFD700; margin: 0; font-size: 2.5em;'>{nom_c}</h1>
                        </div>
                    """,
                        unsafe_allow_html=True,
                    )

                t_noms = [
                    "Datos Generales",
                    "Exp. Laboral",
                    "Form. Académica",
                    "Investigación",
                    "Datos Familiares",
                    "Contratos",
                    "Vacaciones",
                    "Otros Beneficios",
                    "Méritos/Demer.",
                    "Evaluación",
                    "Liquidaciones",
                ]
                h_keys = [
                    "DATOS GENERALES",
                    "EXP. LABORAL",
                    "FORM. ACADEMICA",
                    "INVESTIGACION",
                    "DATOS FAMILIARES",
                    "CONTRATOS",
                    "VACACIONES",
                    "OTROS BENEFICIOS",
                    "MERITOS Y DEMERITOS",
                    "EVALUACION DEL DESEMPEÑO",
                    "LIQUIDACIONES",
                ]

                tabs = st.tabs(t_noms)

                for i, tab in enumerate(tabs):
                    h_name = h_keys[i]
                    with tab:
                        if h_name in dfs and "dni" in dfs[h_name].columns:
                            c_df = dfs[h_name][dfs[h_name]["dni"] == dni_buscado]
                        else:
                            c_df = pd.DataFrame(columns=COLUMNAS.get(h_name, []))

                        # =========================================================================
                        # 📄 PESTAÑA: CONTRATOS
                        # =========================================================================
                        if h_name == "CONTRATOS":
                            df_contratos_base = dfs.get("CONTRATOS", pd.DataFrame())
                
                            if not df_contratos_base.empty and "dni" in df_contratos_base.columns:
                                df_contratos = df_contratos_base[
                                    df_contratos_base["dni"].astype(str) == str(dni_buscado)
                                ]
                            else:
                                df_contratos = pd.DataFrame()
                
                            if not df_contratos.empty:
                                st.dataframe(df_contratos, use_container_width=True)
                                st.markdown("### 📄 Opciones de Certificado")
                
                                df_merged_para_filtro = get_consolidated_contracts(df_contratos)
                
                                if not df_merged_para_filtro.empty:
                                    texto_filas = df_merged_para_filtro.astype(str).apply(
                                        lambda row: " ".join(row).lower(), axis=1
                                    )
                
                                    ha_sido_docente = texto_filas.str.contains(
                                        "docente|profesor|catedra", regex=True
                                    ).any()
                                    ha_sido_administrativo = (
                                        not ha_sido_docente
                                        or (~texto_filas.str.contains("docente|profesor|catedra", regex=True)).any()
                                    )
                
                                    ha_tenido_locacion = texto_filas.str.contains(
                                        "locacion|honorarios|servicios terceros|terceros", regex=True
                                    ).any()
                                    ha_tenido_planilla = (
                                        not ha_tenido_locacion
                                        or (~texto_filas.str.contains("locacion|honorarios|servicios terceros|terceros", regex=True)).any()
                                    )
                                else:
                                    ha_sido_docente = (
                                        ha_sido_administrativo
                                    ) = ha_tenido_planilla = ha_tenido_locacion = False
                
                                opciones_permitidas = ["Automático (Detectar por último contrato)"]
                
                                if ha_sido_administrativo and ha_tenido_planilla:
                                    opciones_permitidas.append("Certificado de Trabajo - Planilla Administrativo")
                                if ha_sido_administrativo and ha_tenido_locacion:
                                    opciones_permitidas.append("Constancia de Servicios - Locación Administrativo")
                                if ha_sido_docente and ha_tenido_planilla:
                                    opciones_permitidas.append("Certificado de Trabajo - Planilla Docente")
                                if ha_sido_docente and ha_tenido_locacion:
                                    opciones_permitidas.append("Constancia de Servicios - Locación Docente")
                
                                if len(opciones_permitidas) == 1:
                                    opciones_permitidas = [
                                        "Automático (Detectar por último contrato)",
                                        "Certificado de Trabajo - Planilla Administrativo",
                                        "Constancia de Servicios - Locación Administrativo",
                                        "Certificado de Trabajo - Planilla Docente",
                                        "Constancia de Servicios - Locación Docente",
                                    ]
                
                                tipo_certificado = st.selectbox(
                                    "Seleccione el tipo de documento a generar:",
                                    opciones_permitidas,
                                    key=f"selector_certificado_{dni_buscado}",
                                )
                
                                try:
                                    word_file = gen_word(nom_c, dni_buscado, df_contratos, tipo_certificado)
                                    st.download_button(
                                        label="📥 Descargar Documento Word",
                                        data=word_file,
                                        file_name=f"Certificado_{dni_buscado}.docx",
                                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                        key=f"btn_descargar_cert_{dni_buscado}",
                                    )
                                except Exception as e:
                                    st.error(f"Error al generar el documento: {e}")
                
                                st.markdown("<br>", unsafe_allow_html=True)
                            else:
                                st.info("No se encontraron registros de contratos para este colaborador.")
                
                        # =========================================================================
                        # 🏖️ PESTAÑA: VACACIONES
                        # =========================================================================
                        elif h_name == "VACACIONES":
                            df_contratos_base = dfs.get("CONTRATOS", pd.DataFrame())
                            df_contratos = (
                                df_contratos_base[df_contratos_base["dni"].astype(str) == str(dni_buscado)]
                                if not df_contratos_base.empty and "dni" in df_contratos_base.columns
                                else pd.DataFrame()
                            )
                
                            df_tc = (
                                df_contratos[
                                    df_contratos["tipo contrato"]
                                    .astype(str)
                                    .str.lower()
                                    .str.contains("planilla", na=False)
                                ]
                                if not df_contratos.empty and "tipo contrato" in df_contratos.columns
                                else pd.DataFrame()
                            )
                
                            detalles = []
                            dias_generados_totales = 0
                            dias_gozados_totales = (
                                pd.to_numeric(c_df["dias gozados"], errors="coerce").sum()
                                if not c_df.empty and "dias gozados" in c_df.columns
                                else 0
                            )
                
                            if not df_tc.empty:
                                df_tc_calc = df_tc.copy()
                                df_tc_calc["f_inicio_dt"] = pd.to_datetime(
                                    df_tc_calc["f_inicio"], errors="coerce"
                                )
                                df_tc_calc["f_fin_dt"] = pd.to_datetime(
                                    df_tc_calc["f_fin"], errors="coerce"
                                )
                
                                start_global = df_tc_calc["f_inicio_dt"].min()
                
                                if pd.notnull(start_global):
                                    curr_start = start_global.date()
                
                                    while curr_start <= date.today():
                                        curr_end = (
                                            pd.to_datetime(curr_start)
                                            + pd.DateOffset(years=1)
                                            - pd.Timedelta(days=1)
                                        ).date()
                                        days_in_p = 0
                
                                        for _, r in df_tc_calc.iterrows():
                                            c_start = (
                                                r["f_inicio_dt"].date()
                                                if pd.notnull(r["f_inicio_dt"])
                                                else None
                                            )
                                            c_end = (
                                                r["f_fin_dt"].date()
                                                if pd.notnull(r["f_fin_dt"])
                                                else None
                                            )
                
                                            if c_start and c_end:
                                                o_start = max(curr_start, c_start)
                                                o_end = min(curr_end, c_end, date.today())
                                                if o_start <= o_end:
                                                    days_in_p += (o_end - o_start).days + 1
                
                                        total_dias_periodo = (curr_end - curr_start).days + 1
                                        gen_p = round((days_in_p / total_dias_periodo) * 30, 2)
                                        p_name = f"{curr_start.year}-{curr_start.year + 1}"
                
                                        goz_p = 0
                                        if not c_df.empty and "periodo" in c_df.columns:
                                            goz_df = c_df[
                                                c_df["periodo"].astype(str).str.strip() == p_name
                                            ]
                                            goz_p = pd.to_numeric(
                                                goz_df["dias gozados"], errors="coerce"
                                            ).sum()
                
                                        if gen_p > 0 or goz_p > 0:
                                            detalles.append(
                                                {
                                                    "Periodo": p_name,
                                                    "Del": curr_start.strftime("%d/%m/%Y"),
                                                    "Al": curr_end.strftime("%d/%m/%Y"),
                                                    "Días Generados": gen_p,
                                                    "Dias Gozados": goz_p,
                                                    "Saldo": round(gen_p - goz_p, 2),
                                                }
                                            )
                
                                        dias_generados_totales += gen_p
                                        curr_start = (
                                            pd.to_datetime(curr_start) + pd.DateOffset(years=1)
                                        ).date()
                
                            saldo_v = round(dias_generados_totales - dias_gozados_totales, 2)
                
                            st.markdown(
                                f"""
                                <div style="display: flex; gap: 15px; margin-bottom: 20px;">
                                    <div style="flex: 1; background-color: #4A0000; padding: 20px; border-radius: 10px; text-align: center; border: 2px solid #FFD700;">
                                        <h2 style="color: #FFD700; margin: 0; font-size: 2.5em;">{dias_generados_totales:.2f}</h2>
                                        <p style="color: #FFFFFF; margin: 0; font-weight: bold; font-size: 1.1em;">Días Generados Totales</p>
                                    </div>
                                    <div style="flex: 1; background-color: #4A0000; padding: 20px; border-radius: 10px; text-align: center; border: 2px solid #FFD700;">
                                        <h2 style="color: #FFD700; margin: 0; font-size: 2.5em;">{dias_gozados_totales:.2f}</h2>
                                        <p style="color: #FFFFFF; margin: 0; font-weight: bold; font-size: 1.1em;">Dias Gozados</p>
                                    </div>
                                    <div style="flex: 1; background-color: #4A0000; padding: 20px; border-radius: 10px; text-align: center; border: 2px solid #FFD700;">
                                        <h2 style="color: #FFD700; margin: 0; font-size: 2.5em;">{saldo_v:.2f}</h2>
                                        <p style="color: #FFFFFF; margin: 0; font-weight: bold; font-size: 1.1em;">Saldo Disponible</p>
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                
                            if detalles:
                                st.markdown(
                                    "<h4 style='color: #FFD700;'>Desglose por Periodos</h4>",
                                    unsafe_allow_html=True,
                                )
                                div_table = (
                                    "<div style='display: flex; flex-direction: column; width: 100%; border: 2px solid #FFD700; border-radius: 8px; overflow: hidden; margin-bottom: 20px;'>"
                                    "<div style='display: flex; background-color: #4A0000; color: #FFD700; font-weight: bold;'>"
                                    "<div style='flex: 1; padding: 12px; text-align: center; border-right: 1px solid #FFD700;'>PERIODO</div>"
                                    "<div style='flex: 1; padding: 12px; text-align: center; border-right: 1px solid #FFD700;'>DEL</div>"
                                    "<div style='flex: 1; padding: 12px; text-align: center; border-right: 1px solid #FFD700;'>AL</div>"
                                    "<div style='flex: 1; padding: 12px; text-align: center; border-right: 1px solid #FFD700;'>DÍAS GENERADOS</div>"
                                    "<div style='flex: 1; padding: 12px; text-align: center; border-right: 1px solid #FFD700;'>DIAS GOZADOS</div>"
                                    "<div style='flex: 1; padding: 12px; text-align: center;'>SALDO</div></div>"
                                )
                                for d in detalles:
                                    div_table += (
                                        f"<div style='display: flex; background-color: #FFF9C4; color: #4A0000; font-weight: bold; border-top: 1px solid #FFD700;'>"
                                        f"<div style='flex: 1; padding: 10px; text-align: center; border-right: 1px solid #FFD700;'>{d['Periodo']}</div>"
                                        f"<div style='flex: 1; padding: 10px; text-align: center; border-right: 1px solid #FFD700;'>{d['Del']}</div>"
                                        f"<div style='flex: 1; padding: 10px; text-align: center; border-right: 1px solid #FFD700;'>{d['Al']}</div>"
                                        f"<div style='flex: 1; padding: 10px; text-align: center; border-right: 1px solid #FFD700;'>{d['Días Generados']:.2f}</div>"
                                        f"<div style='flex: 1; padding: 10px; text-align: center; border-right: 1px solid #FFD700;'>{d['Dias Gozados']:.2f}</div>"
                                        f"<div style='flex: 1; padding: 10px; text-align: center;'>{d['Saldo']:.2f}</div></div>"
                                    )
                                div_table += "</div>"
                                st.markdown(div_table, unsafe_allow_html=True)
                
                            if not c_df.empty:
                                vst = c_df.copy()
                                cols_ocultar = [
                                    c
                                    for c in vst.columns
                                    if c.lower() in ["apellidos y nombres", "apellidos", "nombres"]
                                ]
                                vst = vst.drop(columns=cols_ocultar)
                
                                col_conf = {}
                                for col in vst.columns:
                                    col_lower = str(col).lower()
                                    if "fecha" in col_lower or "f_" in col_lower:
                                        vst[col] = pd.to_datetime(vst[col], errors="coerce").dt.date
                                        col_conf[str(col).upper()] = st.column_config.DateColumn(
                                            format="DD/MM/YYYY",
                                            min_value=date(1950, 1, 1),
                                            max_value=date(2100, 12, 31),
                                        )
                                    elif col_lower.strip() == "periodo":
                                        vst[col] = vst[col].astype(str)
                                        col_conf[str(col).upper()] = st.column_config.TextColumn()
                
                                vst.columns = [str(col).upper() for col in vst.columns]
                                vst = vst.loc[:, ~vst.columns.duplicated()]
                
                                st.dataframe(vst, column_config=col_conf, use_container_width=True)
                
                            st.markdown("---")
                            st.markdown("### 📄 Generar Papeleta de Vacaciones")
                
                            with st.form(key=f"form_papeleta_{dni_buscado}"):
                                col_pap1, col_pap2 = st.columns(2)
                                cargo_def = (
                                    str(df_contratos.iloc[-1]["cargo"])
                                    if not df_contratos.empty and "cargo" in df_contratos.columns
                                    else ""
                                )
                
                                with col_pap1:
                                    p_cargo = st.text_input("Cargo del trabajador:", value=cargo_def)
                                    p_f_ing = st.date_input("Fecha de Ingreso:", value=date.today())
                                    p_per = st.text_input("Periodo Vacacional:", value=f"{date.today().year}")
                
                                with col_pap2:
                                    p_f_ini = st.date_input("Inicio de Vacaciones:", value=date.today())
                                    p_f_fin = st.date_input("Fin de Vacaciones:", value=date.today())
                                    p_dias = st.number_input(
                                        "Días Gozados:", min_value=1, max_value=30, value=7
                                    )
                
                                btn_generar_papeleta = st.form_submit_button("📄 Generar Papeleta")
                
                            if btn_generar_papeleta:
                                try:
                                    papeleta_doc = gen_papeleta_vac(
                                        ape_c,
                                        nom_p_c,
                                        dni_buscado,
                                        p_cargo,
                                        p_f_ing,
                                        p_per,
                                        p_f_ini,
                                        p_f_fin,
                                        p_dias,
                                    )
                                    if papeleta_doc:
                                        st.download_button(
                                            label="📥 Descargar Papeleta Word",
                                            data=papeleta_doc,
                                            file_name=f"Papeleta_Vacaciones_{dni_buscado}.docx",
                                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                            key=f"dl_papeleta_{dni_buscado}",
                                        )
                                    else:
                                        st.error("No se pudo generar el documento de papeleta.")
                                except Exception as err:
                                    st.error(f"Error generando papeleta: {err}")
                
                        # =========================================================================
                        # 🪪 PESTAÑA: DATOS GENERALES
                        # =========================================================================
                        elif h_name == "DATOS GENERALES":
                            vst = c_df.copy() if not c_df.empty else pd.DataFrame()
                        
                            if not vst.empty:
                                ficha = vst.iloc[0]
                        
                                def get_val(names):
                                    ficha_clean = {
                                        str(k)
                                        .lower()
                                        .replace("á", "a")
                                        .replace("é", "e")
                                        .replace("í", "i")
                                        .replace("ó", "o")
                                        .replace("ú", "u")
                                        .replace("_", " "): v
                                        for k, v in ficha.to_dict().items()
                                    }
                                    for name in names:
                                        clean_name = (
                                            name.lower()
                                            .replace("á", "a")
                                            .replace("é", "e")
                                            .replace("í", "i")
                                            .replace("ó", "o")
                                            .replace("ú", "u")
                                            .replace("_", " ")
                                        )
                                        val = ficha_clean.get(clean_name)
                                        if pd.notnull(val) and str(val).strip() not in ["", "-", "0", "nan"]:
                                            return str(val)
                                    return "-"
                        
                                sede = get_val(["SEDE"])
                                sexo = get_val(["SEXO"])
                                est_civil = get_val(["ESTADO CIVIL", "ESTADO_CIVIL"])
                                f_nac = get_val(["FECHA DE NACIMIENTO", "NACIMIENTO"])
                                edad = get_val(["EDAD"])
                                telefono = get_val(["CELULAR", "TELEFONO", "TELÉFONO"])
                                correo = get_val(["CORREO", "EMAIL", "CORREO ELECTRONICO"])
                                direccion = get_val(["DIRECCION", "DIRECCIÓN", "DOMICILIO"])
                        
                                dir_display = "-"
                                if direccion != "-":
                                    query_map = direccion.replace(" ", "+")
                                    link_mapa = f"https://www.google.com/maps/search/?api=1&query={query_map}"
                                    dir_display = f'<a href="{link_mapa}" target="_blank" style="color: #4da3ff; text-decoration: none; font-weight: bold;">📍 {direccion} (Ver en Google Maps 🗺️)</a>'
                        
                                # 1. TARJETA RESUMEN VISUAL
                                st.markdown(
                                    f"""
                                    <div style="background-color: rgba(255, 215, 0, 0.05); padding: 25px; border-radius: 15px; border: 2px solid #FFD700; color: inherit; font-family: sans-serif;">
                                        <h2 style="margin-top:0; color: #FFD700; border-bottom: 1px solid rgba(255,215,0,0.3); padding-bottom:10px;">🪪 Expediente del Personal</h2>
                                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 20px; margin-top: 15px;">
                                            <div><p style="margin:0; font-size: 0.85em; opacity: 0.7;">📍 SEDE</p><p style="margin:0; font-weight: bold; font-size: 1.1em;">{sede}</p></div>
                                            <div><p style="margin:0; font-size: 0.85em; opacity: 0.7;">🚻 SEXO</p><p style="margin:0; font-weight: bold; font-size: 1.1em;">{sexo}</p></div>
                                            <div><p style="margin:0; font-size: 0.85em; opacity: 0.7;">💍 ESTADO CIVIL</p><p style="margin:0; font-weight: bold; font-size: 1.1em;">{est_civil}</p></div>
                                            <div><p style="margin:0; font-size: 0.85em; opacity: 0.7;">🎂 F. NACIMIENTO</p><p style="margin:0; font-weight: bold; font-size: 1.1em;">{f_nac}</p></div>
                                            <div><p style="margin:0; font-size: 0.85em; opacity: 0.7;">🔢 EDAD ACTUAL</p><p style="margin:0; font-weight: bold; font-size: 1.1em;">{edad} años</p></div>
                                            <div><p style="margin:0; font-size: 0.85em; opacity: 0.7;">📱 TELÉFONO / CELULAR</p><p style="margin:0; font-weight: bold; font-size: 1.1em;">{telefono}</p></div>
                                        </div>
                                        <div style="margin-top: 25px; padding-top: 15px; border-top: 1px dashed rgba(255,215,0,0.3);">
                                            <div style="margin-bottom: 15px;">
                                                <p style="margin:0; font-size: 0.85em; opacity: 0.7;">📧 CORREO ELECTRÓNICO</p>
                                                <p style="margin:0; font-weight: bold; font-size: 1.1em;">{correo}</p>
                                            </div>
                                            <div>
                                                <p style="margin:0; font-size: 0.85em; opacity: 0.7;">🏠 DIRECCIÓN DE DOMICILIO</p>
                                                <p style="margin:0; font-size: 1.1em;">{dir_display}</p>
                                            </div>
                                        </div>
                                    </div>
                                    """,
                                    unsafe_allow_html=True,
                                )
                        
                                st.markdown("<br>", unsafe_allow_html=True)
                        
                                # 2. SELECCIÓN DE REGISTRO
                                with st.expander("⚙️ Clic aquí para seleccionar el registro a editar", expanded=True):
                                    if "SEL" not in vst.columns:
                                        vst.insert(0, "SEL", True)
                                    else:
                                        vst["SEL"] = True
                        
                                    ed = st.data_editor(
                                        vst,
                                        hide_index=True,
                                        use_container_width=True,
                                        key="editor_datos_generales"
                                    )
                                    sel = ed[ed["SEL"] == True] if "SEL" in ed.columns else pd.DataFrame()
                        
                                # 3. FORMULARIO DE EDICIÓN
                                if not sel.empty:
                                    row = sel.iloc[0]
                                    st.markdown("### ✏️ Modificar Datos del Colaborador")
                        
                                    with st.form(key="form_editar_datos_generales"):
                                        c1, c2, c3 = st.columns(3)
                        
                                        min_f = date(1930, 1, 1)
                                        max_f = date.today()
                                        fecha_fallback = date(1990, 1, 1)
                        
                                        raw_fnac = str(row.get("fecha de nacimiento", row.get("FECHA DE NACIMIENTO", "")))
                                        try:
                                            parsed_date = pd.to_datetime(raw_fnac).date()
                                            if min_f <= parsed_date <= max_f:
                                                fecha_val = parsed_date
                                            else:
                                                fecha_val = fecha_fallback
                                        except Exception:
                                            fecha_val = fecha_fallback
                        
                                        with c1:
                                            edit_sede = st.text_input("📍 Sede", value=str(row.get("sede", row.get("SEDE", ""))))
                                            edit_sexo = st.selectbox(
                                                "🚻 Sexo",
                                                ["Femenino", "Masculino", "Otro"],
                                                index=0 if "fem" in str(row.get("sexo", "")).lower() else 1
                                            )
                                            edit_est_civil = st.text_input("💍 Estado Civil", value=str(row.get("estado civil", row.get("ESTADO CIVIL", ""))))
                        
                                        with c2:
                                            edit_fnac = st.date_input(
                                                "🎂 Fecha de Nacimiento",
                                                value=fecha_val,
                                                min_value=min_f,
                                                max_value=max_f,
                                                format="YYYY-MM-DD"
                                            )
                                            edit_telefono = st.text_input("📱 Teléfono / Celular", value=str(row.get("celular", row.get("TELEFONO", ""))))
                                            edit_correo = st.text_input("📧 Correo Electrónico", value=str(row.get("correo", row.get("CORREO ELECTRONICO", ""))))
                        
                                        with c3:
                                            edit_direccion = st.text_area("🏠 Dirección de Domicilio", value=str(row.get("direccion", row.get("DIRECCION", ""))))
                        
                                        btn_guardar = st.form_submit_button("💾 Guardar Cambios Modificados", type="primary")
                        
                                        if btn_guardar:
                                            hoy = date.today()
                                            edad_calc = hoy.year - edit_fnac.year - ((hoy.month, hoy.day) < (edit_fnac.month, edit_fnac.day))
                        
                                            dni_colab = str(row.get("dni", row.get("DNI", "")))
                                            idx = dfs["DATOS GENERALES"][dfs["DATOS GENERALES"]["dni"].astype(str) == dni_colab].index
                        
                                            if not idx.empty:
                                                i = idx[0]
                                                for col in dfs["DATOS GENERALES"].columns:
                                                    c_norm = str(col).lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("_", " ")
                                                    if c_norm in ["sede"]:
                                                        dfs["DATOS GENERALES"].at[i, col] = edit_sede
                                                    elif c_norm in ["sexo"]:
                                                        dfs["DATOS GENERALES"].at[i, col] = edit_sexo
                                                    elif c_norm in ["estado civil"]:
                                                        dfs["DATOS GENERALES"].at[i, col] = edit_est_civil
                                                    elif c_norm in ["fecha de nacimiento", "nacimiento"]:
                                                        dfs["DATOS GENERALES"].at[i, col] = str(edit_fnac)
                                                    elif c_norm in ["edad"]:
                                                        dfs["DATOS GENERALES"].at[i, col] = edad_calc
                                                    elif c_norm in ["celular", "telefono", "telefono / celular"]:
                                                        dfs["DATOS GENERALES"].at[i, col] = edit_telefono
                                                    elif c_norm in ["correo", "email", "correo electronico"]:
                                                        dfs["DATOS GENERALES"].at[i, col] = edit_correo
                                                    elif c_norm in ["direccion", "domicilio"]:
                                                        dfs["DATOS GENERALES"].at[i, col] = edit_direccion
                        
                                                if "save_data" in globals():
                                                    save_data(dfs)
                                                elif "exportar_df_a_sheets" in globals():
                                                    exportar_df_a_sheets(dfs)
                        
                                                st.success("✅ ¡Datos actualizados y guardados correctamente!")
                                                st.rerun()
                        
                                    # 4. ACCIÓN ÚNICA DE ELIMINACIÓN (SIN BOTÓN REDUNDANTE DE GUARDAR)
                                    st.markdown("<br>", unsafe_allow_html=True)
                                    if st.button("🗑️ Eliminar Registro Seleccionado", use_container_width=True):
                                        dni_colab = str(row.get("dni", row.get("DNI", "")))
                                        dfs["DATOS GENERALES"] = dfs["DATOS GENERALES"][dfs["DATOS GENERALES"]["dni"].astype(str) != dni_colab]
                                        
                                        if "save_data" in globals():
                                            save_data(dfs)
                                        elif "exportar_df_a_sheets" in globals():
                                            exportar_df_a_sheets(dfs)
                        
                                        st.success("🗑️ Registro eliminado correctamente.")
                                        st.rerun()
                        
                                else:
                                    st.warning("📌 Marca la casilla **SEL** para habilitar la modificación de campos.")
                        
                            else:
                                st.info(f"Sin información registrada en {h_name}.")
                
                        # =========================================================
                        # 🔬 PESTAÑA: INVESTIGACIÓN
                        # =========================================================
                        elif h_name == "INVESTIGACION":
                            vst = c_df.copy() if not c_df.empty else pd.DataFrame()
                            if not vst.empty:
                                if "SEL" not in vst.columns:
                                    vst.insert(0, "SEL", False)
                
                                col_izq, col_der = st.columns([2, 1])
                
                                df_inv = dfs.get("INVESTIGACION", pd.DataFrame())
                                col_dni_inv = "dni" if "dni" in df_inv.columns else "DNI"
                
                                inv_empleado = pd.DataFrame()
                                if not df_inv.empty and col_dni_inv in df_inv.columns:
                                    inv_empleado = df_inv[
                                        df_inv[col_dni_inv].astype(str) == str(dni_buscado)
                                    ]
                
                                conteo_pub = conteo_fondos = conteo_sem = 0
                
                                with col_izq:
                                    st.markdown(
                                        "<h3 style='color: #FFD700;'>🔬 Registro de Actividades de Investigación</h3>",
                                        unsafe_allow_html=True,
                                    )
                                    if inv_empleado.empty:
                                        st.markdown(
                                            "<p style='color:#DDDDDD;'>No hay registros de investigación para este colaborador.</p>",
                                            unsafe_allow_html=True,
                                        )
                                    else:
                                        for idx, row in inv_empleado.iterrows():
                                            tipo = str(
                                                row.get(
                                                    "tipo de registro",
                                                    row.get("TIPO DE REGISTRO", "Otro"),
                                                )
                                            ).strip()
                
                                            if tipo == "Datos Generales (CTI Vitae / RENACYT)":
                                                renacyt = row.get("codigo renacyt", "N/A")
                                                nivel = row.get("nivel renacyt", "N/A")
                                                link = row.get("enlace cti vitae", "#")
                                                st.markdown(
                                                    f"""
                                                <div style='background-color: #E8F4F8; padding: 15px; border-radius: 8px; border-left: 6px solid #00AEEF; margin-bottom: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: 1px solid #CCCCCC;'>
                                                    <div style='color: #000000; font-size: 1.1em; font-weight: bold; margin-bottom: 5px;'>👤 Perfil CTI Vitae / RENACYT</div>
                                                    <div style='color: #222222; font-size: 0.95em;'>
                                                        <strong>Código:</strong> {renacyt} <br>
                                                        <strong>Nivel RENACYT:</strong> {nivel} <br>
                                                        <a href="{link}" target="_blank" style="color: #00AEEF; text-decoration: none;">🔗 Ver Perfil CTI Vitae</a>
                                                    </div>
                                                </div>
                                                """,
                                                    unsafe_allow_html=True,
                                                )
                
                                            elif tipo == "Publicación Científica":
                                                conteo_pub += 1
                                                titulo = row.get("titulo de publicacion", "N/A")
                                                bd = row.get("base de datos", "N/A")
                                                revista = row.get("nombre de revista", "N/A")
                                                anio = row.get("año de publicacion", "N/A")
                                                st.markdown(
                                                    f"""
                                                <div style='background-color: #F9F6EE; padding: 15px; border-radius: 8px; border-left: 6px solid #FF8C00; margin-bottom: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: 1px solid #CCCCCC;'>
                                                    <div style='color: #000000; font-size: 1.1em; font-weight: bold; margin-bottom: 5px;'>📄 Publicación: {titulo}</div>
                                                    <div style='color: #222222; font-size: 0.95em;'>
                                                        <strong>Revista:</strong> {revista} ({anio}) <br>
                                                        <strong>Indexación:</strong> {bd} - <strong>Cuartil:</strong> {row.get('cuartil', 'N/A')}
                                                    </div>
                                                </div>
                                                """,
                                                    unsafe_allow_html=True,
                                                )
                
                                            elif tipo == "Fondo Concursable":
                                                conteo_fondos += 1
                                                titulo_proy = row.get("nombre del proyecto", "N/A")
                                                entidad = row.get("entidad financiadora", "N/A")
                                                estado = row.get("estado del proyecto", "N/A")
                                                st.markdown(
                                                    f"""
                                                <div style='background-color: #F4FDE8; padding: 15px; border-radius: 8px; border-left: 6px solid #4CAF50; margin-bottom: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: 1px solid #CCCCCC;'>
                                                    <div style='color: #000000; font-size: 1.1em; font-weight: bold; margin-bottom: 5px;'>💰 Proyecto Financiado: {titulo_proy}</div>
                                                    <div style='color: #222222; font-size: 0.95em;'>
                                                        <strong>Entidad:</strong> {entidad} <br>
                                                        <strong>Rol:</strong> {row.get('rol en el proyecto', 'N/A')} <br>
                                                        <strong>Estado:</strong> <span style="color: {'green' if estado=='Finalizado' else 'blue'}; font-weight: bold;">{estado}</span>
                                                    </div>
                                                </div>
                                                """,
                                                    unsafe_allow_html=True,
                                                )
                
                                            elif tipo == "Semillero de Investigación":
                                                conteo_sem += 1
                                                nombre_sem = row.get("nombre del semillero", "N/A")
                                                rol_sem = row.get("rol en el semillero", "N/A")
                                                estado_sem = row.get("estado del semillero", "N/A")
                                                st.markdown(
                                                    f"""
                                                <div style='background-color: #F8E8F8; padding: 15px; border-radius: 8px; border-left: 6px solid #9C27B0; margin-bottom: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: 1px solid #CCCCCC;'>
                                                    <div style='color: #000000; font-size: 1.1em; font-weight: bold; margin-bottom: 5px;'>🌱 Semillero: {nombre_sem}</div>
                                                    <div style='color: #222222; font-size: 0.95em;'>
                                                        <strong>Rol:</strong> {rol_sem} <br>
                                                        <strong>Estado:</strong> {estado_sem}
                                                    </div>
                                                </div>
                                                """,
                                                    unsafe_allow_html=True,
                                                )
                
                                # (Continuación de la pestaña INVESTIGACION - Columna Derecha)
                                with col_der:
                                    st.markdown("<h3 style='color: #FFD700;'>📊 Resumen</h3>", unsafe_allow_html=True)
                                    html_resumen_inv = f"""
                                    <div style='background-color: #4A0000; padding: 20px; border-radius: 10px; border: 2px solid #FFD700; box-shadow: 2px 2px 10px rgba(0,0,0,0.5); position: sticky; top: 50px;'>
                                        <h4 style='color: #FFD700; margin-bottom: 15px; text-align: center; border-bottom: 1px solid #FFD700; padding-bottom: 10px;'>Impacto Científico</h4>
                                        <div style='margin-bottom: 15px;'>
                                            <p style='margin: 0; color: #FFFFFF; font-size: 0.9em;'>📄 Publicaciones Indexadas</p>
                                            <p style='margin: 0; color: #FF8C00; font-size: 1.4em; font-weight: bold;'>{conteo_pub}</p>
                                        </div>
                                        <div style='margin-bottom: 15px;'>
                                            <p style='margin: 0; color: #FFFFFF; font-size: 0.9em;'>💰 Fondos Concursables</p>
                                            <p style='margin: 0; color: #4CAF50; font-size: 1.4em; font-weight: bold;'>{conteo_fondos}</p>
                                        </div>
                                        <div style='margin-bottom: 15px;'>
                                            <p style='margin: 0; color: #FFFFFF; font-size: 0.9em;'>🌱 Semilleros Liderados</p>
                                            <p style='margin: 0; color: #9C27B0; font-size: 1.4em; font-weight: bold;'>{conteo_sem}</p>
                                        </div>
                                    </div>
                                    """
                                    st.markdown(html_resumen_inv, unsafe_allow_html=True)
                
                            # =========================================================
                            # 📌 ESTO SE MUESTRA SI 'vst' ESTÁ VACÍO
                            # =========================================================
                            else:
                                if not c_df.empty:
                                    st.dataframe(c_df, use_container_width=True)
                                else:
                                    st.info(f"Sin información registrada en {h_name}.")
                
                            # Expansor también dentro de INVESTIGACION
                            st.markdown("<br>", unsafe_allow_html=True)
                            with st.expander("⚙️ Clic aquí para Editar o Eliminar un Registro de Investigación"):
                                st.markdown("<p style='color:#DDDDDD;'>Activa la casilla <b>SEL</b> para modificar o eliminar un registro.</p>", unsafe_allow_html=True)
                                st.markdown("""<style>[data-testid="stDataEditor"] { border: 2px solid #FFD700 !important; border-radius: 10px !important; }</style>""", unsafe_allow_html=True)
                                
                                conf = col_conf if 'col_conf' in locals() else {}
                                ed = st.data_editor(vst, hide_index=True, use_container_width=True, column_config=conf, key=f"ed_{h_name}_oculta")
                                sel = ed[ed["SEL"] == True] if "SEL" in ed.columns else pd.DataFrame()
                
                        # ==========================================
                        # NUEVO DISEÑO: EXPERIENCIA LABORAL Y CÁLCULOS
                        # ==========================================
                        elif h_name == "EXP. LABORAL":
                            vst_df = c_df.copy() if not c_df.empty else pd.DataFrame()
                            
                            if not vst_df.empty and "SEL" not in vst_df.columns:
                                vst_df.insert(0, "SEL", False)
                                
                            # --- Funciones Auxiliares ---
                            def calcular_meses(f_ini, f_fin):
                                try:
                                    inicio = pd.to_datetime(f_ini, errors='coerce')
                                    fin = pd.to_datetime(f_fin, errors='coerce')
                                    if pd.isna(inicio) or pd.isna(fin): 
                                        return 0
                                    return max(0, int((fin - inicio).days / 30.44))
                                except Exception:
                                    return 0
                                    
                            def dar_formato_fecha(fecha_str):
                                try:
                                    if pd.isna(fecha_str) or str(fecha_str).strip() in ["", "NaT", "None"]: 
                                        return "N/A"
                                    return pd.to_datetime(fecha_str).strftime('%d/%m/%Y')
                                except Exception:
                                    return str(fecha_str)
                        
                            def formato_tiempo(total_meses):
                                anios = total_meses // 12
                                meses = total_meses % 12
                                if anios > 0 and meses > 0: 
                                    return f"{anios} años y {meses} meses"
                                elif anios > 0: 
                                    return f"{anios} años"
                                elif meses > 0: 
                                    return f"{meses} meses"
                                else: 
                                    return "0 meses"
                        
                            # --- Cargar datos de Contratos ---
                            df_contratos = dfs.get("CONTRATOS", pd.DataFrame())
                            col_dni_contratos = "DNI" if "DNI" in df_contratos.columns else "dni"
                            
                            contratos_empleado = pd.DataFrame()
                            if not df_contratos.empty and col_dni_contratos in df_contratos.columns:
                                contratos_empleado = df_contratos[df_contratos[col_dni_contratos].astype(str) == str(dni_buscado)]
                            
                            meses_docente = 0
                            meses_admin = 0
                        
                            # --- Distribución en Columnas ---
                            col_izq, col_der = st.columns([2, 1])
                        
                            # -------------------------------------------------------------
                            # COLUMNA IZQUIERDA: Experiencias (Interna y Externa)
                            # -------------------------------------------------------------
                            with col_izq:
                                st.markdown("<h3 style='color: #FFD700;'>🏢 Experiencia Interna (Universidad Roosevelt)</h3>", unsafe_allow_html=True)
                                if contratos_empleado.empty:
                                    st.markdown("<p style='color:#DDDDDD;'>No hay contratos internos registrados.</p>", unsafe_allow_html=True)
                                else:
                                    for idx, row in contratos_empleado.iterrows():
                                        f_ini = row.get('f_inicio', row.get('F_INICIO', 'N/A'))
                                        f_fin = row.get('f_fin', row.get('F_FIN', 'N/A'))
                                        
                                        f_ini_str = dar_formato_fecha(f_ini)
                                        f_fin_str = dar_formato_fecha(f_fin)
                                        
                                        puesto = row.get('cargo', row.get('CARGO', row.get('PUESTO', 'N/A')))
                                        tipo_trabajador_raw = str(row.get('TIPO DE TRABAJADOR', row.get('tipo de trabajador', 'Administrativo')))
                                        tipo_exp = "Docente" if "docente" in tipo_trabajador_raw.lower() else "Administrativo"
                                        
                                        meses_calc = calcular_meses(f_ini, f_fin)
                                        if tipo_exp == "Docente": 
                                            meses_docente += meses_calc
                                        else: 
                                            meses_admin += meses_calc
                                        
                                        st.markdown(f"""
                                        <div style='background-color: #F9F6EE; padding: 15px; border-radius: 8px; border-left: 6px solid #4A0000; margin-bottom: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: 1px solid #CCCCCC;'>
                                            <div style='color: #000000; font-size: 1.1em; font-weight: bold; margin-bottom: 5px;'>{puesto} <span style='font-size: 0.85em; color: #555555;'>(Interno - {tipo_exp})</span></div>
                                            <div style='color: #222222; font-size: 0.95em;'>
                                                <strong>Lugar:</strong> Universidad Roosevelt <br>
                                                <strong>Periodo:</strong> {f_ini_str} hasta {f_fin_str} <br>
                                                <strong>Tipo de Contrato:</strong> {row.get('tipo contrato', row.get('TIPO CONTRATO', 'N/A'))}
                                            </div>
                                        </div>
                                        """, unsafe_allow_html=True)
                                
                                st.markdown("<h3 style='color: #FFD700; margin-top: 20px;'>💼 Experiencia Externa Registrada</h3>", unsafe_allow_html=True)
                                if vst_df.empty:
                                    st.markdown("<p style='color:#DDDDDD;'>No hay experiencia externa registrada.</p>", unsafe_allow_html=True)
                                else:
                                    for idx, row in vst_df.iterrows():
                                        f_ini = row.get('FECHA DE INICIO', row.get('fecha de inicio', 'N/A'))
                                        f_fin = row.get('FECHA DE FIN', row.get('fecha de fin', 'N/A'))
                                        
                                        f_ini_str = dar_formato_fecha(f_ini)
                                        f_fin_str = dar_formato_fecha(f_fin)
                                        
                                        tipo_exp_raw = str(row.get('TIPO DE EXPERIENCIA', row.get('tipo de experiencia', 'Administrativo')))
                                        tipo_exp = "Docente" if "docente" in tipo_exp_raw.lower() else "Administrativo"
                                        
                                        meses_calc = calcular_meses(f_ini, f_fin)
                                        if tipo_exp == "Docente": 
                                            meses_docente += meses_calc
                                        else: 
                                            meses_admin += meses_calc
                                        
                                        puesto_ext = row.get('PUESTO', row.get('puesto', 'N/A'))
                                        lugar_ext = row.get('LUGAR', row.get('lugar', 'N/A'))
                                        motivo_ext = row.get('MOTIVO DE CESE', row.get('motivo de cese', 'N/A'))
                                        
                                        st.markdown(f"""
                                        <div style='background-color: #F9F6EE; padding: 15px; border-radius: 8px; border-left: 6px solid #004A80; margin-bottom: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: 1px solid #CCCCCC;'>
                                            <div style='color: #000000; font-size: 1.1em; font-weight: bold; margin-bottom: 5px;'>{puesto_ext} <span style='font-size: 0.85em; color: #555555;'>({tipo_exp.capitalize()})</span></div>
                                            <div style='color: #222222; font-size: 0.95em;'>
                                                <strong>Lugar:</strong> {lugar_ext} <br>
                                                <strong>Periodo:</strong> {f_ini_str} hasta {f_fin_str} <br>
                                                <strong>Motivo de cese:</strong> {motivo_ext}
                                            </div>
                                        </div>
                                        """, unsafe_allow_html=True)
                        
                            # -------------------------------------------------------------
                            # COLUMNA DERECHA: Resumen y Plan de Carrera
                            # -------------------------------------------------------------
                            with col_der:
                                st.markdown("<h3 style='color: #FFD700;'>📊 Resumen</h3>", unsafe_allow_html=True)
                                
                                html_resumen = f"""
                                <div style='background-color: #4A0000; padding: 20px; border-radius: 10px; border: 2px solid #FFD700; box-shadow: 2px 2px 10px rgba(0,0,0,0.5); position: sticky; top: 50px;'>
                                    <h4 style='color: #FFD700; margin-bottom: 15px; text-align: center; border-bottom: 1px solid #FFD700; padding-bottom: 10px;'>Tiempo Total Calculado</h4>
                                    <div style='margin-bottom: 15px;'>
                                        <p style='margin: 0; color: #FFFFFF; font-size: 0.9em;'>👨‍🏫 Como Docente</p>
                                        <p style='margin: 0; color: #FFD700; font-size: 1.2em; font-weight: bold;'>{formato_tiempo(meses_docente)}</p>
                                    </div>
                                    <div style='margin-bottom: 15px;'>
                                        <p style='margin: 0; color: #FFFFFF; font-size: 0.9em;'>💼 Como Administrativo</p>
                                        <p style='margin: 0; color: #FFD700; font-size: 1.2em; font-weight: bold;'>{formato_tiempo(meses_admin)}</p>
                                    </div>
                                    <div style='margin-top: 15px; padding-top: 10px; border-top: 1px solid #FFD700;'>
                                        <p style='margin: 0; color: #FFFFFF; font-size: 0.9em;'>🌟 Experiencia General</p>
                                        <p style='margin: 0; color: #00FF00; font-size: 1.4em; font-weight: bold;'>{formato_tiempo(meses_docente + meses_admin)}</p>
                                    </div>
                                </div>
                                """
                                st.markdown(html_resumen, unsafe_allow_html=True)
                        
                            # -------------------------------------------------------------
                            # SECCIÓN DE GESTIÓN: REGISTRAR, EDITAR Y ELIMINAR
                            # -------------------------------------------------------------
                            st.markdown("<br>", unsafe_allow_html=True)
                            
                            # 1. FORMULARIO PARA INGRESAR NUEVO REGISTRO
                            with st.expander("➕ Nuevo Registro de Experiencia Externa", expanded=True):
                                with st.form(key="form_nueva_exp_externa", clear_on_submit=True):
                                    st.markdown("<h4 style='color: #4A0000;'>Ingresa los datos de la nueva experiencia laboral</h4>", unsafe_allow_html=True)
                                    
                                    c_f1, c_f2 = st.columns(2)
                                    with c_f1:
                                        nuevo_puesto = st.text_input("Puesto / Cargo *", placeholder="Ej. Jefe de Recursos Humanos")
                                        nuevo_lugar = st.text_input("Lugar / Empresa / Institución *", placeholder="Ej. Empresa XYZ S.A.C.")
                                        tipo_exp_opt = st.selectbox("Tipo de Experiencia *", ["Administrativo", "Docente"])
                                        
                                    with c_f2:
                                        f_inicio = st.date_input("Fecha de Inicio")
                                        f_fin = st.date_input("Fecha de Fin")
                                        motivo_cese = st.text_input("Motivo de Cese", placeholder="Ej. Renuncia voluntaria / Fin de contrato")
                                    
                                    btn_guardar = st.form_submit_button("💾 Guardar Registro en EXP. LABORAL", use_container_width=True)
                                    
                                    if btn_guardar:
                                        if not nuevo_puesto or not nuevo_lugar:
                                            st.error("⚠️ Los campos 'Puesto' y 'Lugar' son obligatorios.")
                                        else:
                                            nueva_fila = {
                                                "dni": str(dni_buscado),
                                                "DNI": str(dni_buscado),
                                                "PUESTO": nuevo_puesto,
                                                "LUGAR": nuevo_lugar,
                                                "TIPO DE EXPERIENCIA": tipo_exp_opt,
                                                "FECHA DE INICIO": f_inicio.strftime('%Y-%m-%d') if f_inicio else "",
                                                "FECHA DE FIN": f_fin.strftime('%Y-%m-%d') if f_fin else "",
                                                "MOTIVO DE CESE": motivo_cese
                                            }
                                            
                                            if "EXP. LABORAL" not in dfs or dfs["EXP. LABORAL"].empty:
                                                dfs["EXP. LABORAL"] = pd.DataFrame([nueva_fila])
                                            else:
                                                dfs["EXP. LABORAL"] = pd.concat([dfs["EXP. LABORAL"], pd.DataFrame([nueva_fila])], ignore_index=True)
                                                
                                            st.success("✅ ¡Experiencia externa registrada con éxito!")
                                            st.rerun()
                        
                            # 2. EDICIÓN / ELIMINACIÓN DE REGISTROS EXISTENTES
                            with st.expander("⚙️ Clic aquí para Editar o Eliminar Experiencia Externa"):
                                if vst_df.empty:
                                    st.info("No hay registros para modificar o eliminar.")
                                else:
                                    st.markdown("<p style='color:#DDDDDD;'>Marca la casilla <b>SEL</b> para eliminar los registros seleccionados.</p>", unsafe_allow_html=True)
                                    col_conf_exp = col_conf if 'col_conf' in locals() else {}
                                    
                                    ed = st.data_editor(
                                        vst_df, 
                                        hide_index=True, 
                                        use_container_width=True, 
                                        column_config=col_conf_exp, 
                                        key=f"ed_{h_name}_oculta"
                                    )
                                    
                                    if "SEL" in ed.columns:
                                        sel = ed[ed["SEL"] == True]
                                        if not sel.empty:
                                            st.warning(f"Has seleccionado {len(sel)} registro(s).")
                                            if st.button("🗑️ Eliminar Seleccionados", key=f"btn_del_{h_name}"):
                                                # Excluir registros seleccionados de la base global
                                                indices_a_borrar = sel.index
                                                c_df_filtrado = c_df.drop(indices_a_borrar, errors='ignore')
                                                dfs["EXP. LABORAL"] = dfs["EXP. LABORAL"][dfs["EXP. LABORAL"]["dni"].astype(str) != str(dni_buscado)]
                                                dfs["EXP. LABORAL"] = pd.concat([dfs["EXP. LABORAL"], c_df_filtrado], ignore_index=True)
                                                
                                                st.success("Registros eliminados correctamente.")
                                                st.rerun()
                    
                        # ==========================================
                        # NUEVO DISEÑO: CONTRATOS
                        # ==========================================
                        elif h_name == "CONTRATOS":
                            col_conf_cfg = col_conf if 'col_conf' in locals() and isinstance(col_conf, dict) else {}
                            vst_df = vst if 'vst' in locals() and isinstance(vst, pd.DataFrame) else pd.DataFrame()
                            
                            if vst_df.empty:
                                st.markdown("<p style='color:#DDDDDD;'>No hay contratos registrados para este colaborador.</p>", unsafe_allow_html=True)
                            else:
                                for _, row in vst_df.iterrows():
                                    f_inicio = row.get('F_INICIO', row.get('f_inicio', 'N/A'))
                                    f_fin = row.get('F_FIN', row.get('f_fin', 'N/A'))
                                    cargo = row.get('CARGO', row.get('cargo', 'N/A'))
                                    tipo = row.get('TIPO CONTRATO', row.get('tipo contrato', 'N/A'))
                                    estado = str(row.get('ESTADO', row.get('estado', 'N/A'))).strip()
                                    
                                    color_borde = "#4CAF50" if estado.upper() == "ACTIVO" else "#F44336"
                                    
                                    st.markdown(f"""
                                    <div style='background-color: #FFFFFF; padding: 15px; border-radius: 8px; border-left: 6px solid {color_borde}; margin-bottom: 10px; border: 1px solid #CCCCCC;'>
                                        <div style='color: #000000; font-size: 1.1em; font-weight: bold; margin-bottom: 5px;'>{cargo}</div>
                                        <div style='color: #111111; font-size: 0.95em;'>
                                            <strong>📅 Periodo:</strong> {f_inicio} hasta {f_fin} <br>
                                            <strong>📝 Tipo de Contrato:</strong> {tipo} <br>
                                            <strong>📌 Estado:</strong> <span style='color: {color_borde}; font-weight: bold;'>{estado}</span>
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)
                        
                            st.markdown("<br>", unsafe_allow_html=True)
                            with st.expander("⚙️ Clic aquí para Editar o Eliminar Contratos"):
                                st.markdown("<p style='color:#DDDDDD;'>Activa la casilla <b>SEL</b> en la tabla de abajo para modificar o eliminar un registro.</p>", unsafe_allow_html=True)
                                st.markdown("""<style>[data-testid="stDataEditor"] { border: 2px solid #FFD700 !important; border-radius: 8px !important; }</style>""", unsafe_allow_html=True)
                                
                                ed = st.data_editor(vst_df, hide_index=True, use_container_width=True, column_config=col_conf_cfg, key=f"ed_{h_name}_oculta")
                                sel = ed[ed["SEL"] == True] if "SEL" in ed.columns else pd.DataFrame()
                        
                        # ==========================================
                        # NUEVO DISEÑO: VACACIONES
                        # ==========================================
                        elif h_name == "VACACIONES":
                            col_conf_cfg = col_conf if 'col_conf' in locals() and isinstance(col_conf, dict) else {}
                            vst_df = vst if 'vst' in locals() and isinstance(vst, pd.DataFrame) else pd.DataFrame()
                            
                            st.markdown("<br>", unsafe_allow_html=True)
                            with st.expander("⚙️ Clic aquí para ver el Detalle Completo, Editar o Eliminar Vacaciones"):
                                st.markdown("<p style='color:#000000; background-color:#FFD700; padding:5px; border-radius:5px;'><b>Detalle de registros:</b> Activa la casilla <b>SEL</b> para modificar o eliminar.</p>", unsafe_allow_html=True)
                                st.markdown("""<style>[data-testid="stDataEditor"] { border: 2px solid #FFD700 !important; border-radius: 8px !important; }</style>""", unsafe_allow_html=True)
                                
                                ed = st.data_editor(vst_df, hide_index=True, use_container_width=True, column_config=col_conf_cfg, key=f"ed_{h_name}_oculta")
                                sel = ed[ed["SEL"] == True] if "SEL" in ed.columns else pd.DataFrame()
                        
                        # ==========================================
                        # NUEVO DISEÑO: FORMACIÓN ACADÉMICA
                        # ==========================================
                        elif h_name == "FORM. ACADEMICA":
                            st.markdown("<h3 style='color: #FFD700; margin-bottom: 20px;'>🎓 Resumen de Formación Académica</h3>", unsafe_allow_html=True)
                        
                            # Identificación flexible de la columna 'tipo de estudio'
                            col_tipo = "TIPO DE ESTUDIO" if "TIPO DE ESTUDIO" in vst.columns else ("tipo de estudio" if "tipo de estudio" in vst.columns else None)
                        
                            if not vst.empty and col_tipo and col_tipo in vst.columns:
                                # 1. Filtro: Estudios sin grado, terminados o inconclusos
                                mask_estudios = vst[col_tipo].str.contains("Terminados|Inconclusos|Sin grado", case=False, na=False)
                                df_estudios = vst[mask_estudios]
                        
                                # 2. Filtro: Grados y Títulos (excluyendo a los de arriba)
                                mask_grados = vst[col_tipo].str.contains("Grado|Títul|Titul", case=False, na=False) & ~mask_estudios
                                df_grados = vst[mask_grados]
                        
                                # 3. Especializaciones, Diplomados y Cursos
                                df_especi = vst[vst[col_tipo].str.contains("Especialización|Especializaciones", case=False, na=False)]
                                df_diplo = vst[vst[col_tipo].str.contains("Diplomado", case=False, na=False)]
                                df_cursos = vst[vst[col_tipo].str.contains("Curso", case=False, na=False)]
                            else:
                                df_grados = df_estudios = df_especi = df_diplo = df_cursos = pd.DataFrame()
                        
                            # Función auxiliar para evitar celdas vacías (N/A)
                            def get_val(r, opciones):
                                for op in opciones:
                                    if op in r:
                                        val = r[op]
                                        if pd.notna(val) and str(val).strip() != "":
                                            return str(val)
                                return "N/A"
                        
                            # --- 1. GRADOS Y TÍTULOS (Vista de ancho completo) ---
                            st.markdown("<h4 style='color: #FFD700; font-weight: bold; border-bottom: 2px solid #FFD700; padding-bottom: 5px;'>📜 Grados y Títulos</h4>", unsafe_allow_html=True)
                            if df_grados.empty:
                                st.markdown("<p style='color:#DDDDDD;'>No hay grados o títulos registrados.</p>", unsafe_allow_html=True)
                            else:
                                for _, row in df_grados.iterrows():
                                    grado = get_val(row, ['grado o titulo obtenido', 'GRADO O TITULO OBTENIDO', 'grado o título obtenido'])
                                    inst = get_val(row, ['institucion educativa', 'INSTITUCION EDUCATIVA', 'institución educativa'])
                                    mencion = get_val(row, ['mencion (especialidad / carrera / etc)', 'MENCION (ESPECIALIDAD / CARRERA / ETC)', 'mención'])
                                    anio = get_val(row, ['AÑO', 'año'])
                        
                                    st.markdown(f"""
                                    <div style='background-color: #FFFFFF; padding: 15px; border-radius: 8px; border: 1px solid #CCCCCC; border-left: 6px solid #FFC107; margin-bottom: 10px;'>
                                        <div style='margin-bottom: 5px; color: #000000; font-size: 1.1em; font-weight: bold;'>{grado}</div>
                                        <div style='margin: 2px 0; color: #000000;'><strong>Institución:</strong> {inst}</div>
                                        <div style='margin: 2px 0; color: #000000;'><strong>Mención:</strong> {mencion}</div>
                                        <div style='margin: 2px 0; color: #000000;'><strong>Año:</strong> {anio}</div>
                                    </div>
                                    """, unsafe_allow_html=True)
                        
                            # --- COLUMNAS DE DETALLE ---
                            col_izq_acad, col_der_acad = st.columns(2)
                        
                            with col_izq_acad:
                                # --- 2. ESTUDIOS SIN GRADO / INCONCLUSOS ---
                                st.markdown("<h4 style='color: #FFD700; font-weight: bold; margin-top: 15px; border-bottom: 2px solid #FFD700; padding-bottom: 5px;'>🚧 Estudios Sin Grado / Inconclusos</h4>", unsafe_allow_html=True)
                                if df_estudios.empty:
                                    st.markdown("<p style='color:#DDDDDD;'>No registrados.</p>", unsafe_allow_html=True)
                                else:
                                    for _, row in df_estudios.iterrows():
                                        inst = get_val(row, ['institucion educativa', 'INSTITUCION EDUCATIVA', 'institución educativa'])
                                        mencion = get_val(row, ['mencion (especialidad / carrera / etc)', 'MENCION (ESPECIALIDAD / CARRERA / ETC)', 'mención'])
                                        anio = get_val(row, ['AÑO', 'año'])
                                        estado = get_val(row, ['ESTADO', 'estado'])
                        
                                        st.markdown(f"""
                                        <div style='background-color: #FFFFFF; padding: 15px; border-radius: 8px; border: 1px solid #CCCCCC; border-left: 6px solid #FF5722; margin-bottom: 10px;'>
                                            <div style='margin-bottom: 5px; color: #000000; font-size: 1em; font-weight: bold;'>{mencion}</div>
                                            <div style='margin: 2px 0; color: #000000;'><strong>Institución:</strong> {inst}</div>
                                            <div style='margin: 2px 0; color: #000000;'><strong>Estado:</strong> <span style='color: #D84315; font-weight: bold;'>{estado}</span> | <strong>Año:</strong> {anio}</div>
                                        </div>
                                        """, unsafe_allow_html=True)
                        
                                # --- 3. ESPECIALIZACIONES ---
                                st.markdown("<h4 style='color: #FFD700; font-weight: bold; margin-top: 15px; border-bottom: 2px solid #FFD700; padding-bottom: 5px;'>🔬 Especializaciones</h4>", unsafe_allow_html=True)
                                if df_especi.empty:
                                    st.markdown("<p style='color:#DDDDDD;'>No registradas.</p>", unsafe_allow_html=True)
                                else:
                                    for _, row in df_especi.iterrows():
                                        inst = get_val(row, ['institucion educativa', 'INSTITUCION EDUCATIVA', 'institución educativa'])
                                        mencion = get_val(row, ['mencion (especialidad / carrera / etc)', 'MENCION (ESPECIALIDAD / CARRERA / ETC)', 'mención'])
                                        anio = get_val(row, ['AÑO', 'año'])
                                        horas = get_val(row, ['horas academicas', 'HORAS ACADEMICAS', 'horas académicas'])
                        
                                        st.markdown(f"""
                                        <div style='background-color: #FFFFFF; padding: 15px; border-radius: 8px; border: 1px solid #CCCCCC; border-left: 6px solid #9C27B0; margin-bottom: 10px;'>
                                            <div style='margin-bottom: 5px; color: #000000; font-size: 1em; font-weight: bold;'>{mencion}</div>
                                            <div style='margin: 2px 0; color: #000000;'><strong>Institución:</strong> {inst}</div>
                                            <div style='margin: 2px 0; color: #000000;'><strong>Horas Ac.:</strong> {horas} hrs | <strong>Año:</strong> {anio}</div>
                                        </div>
                                        """, unsafe_allow_html=True)
                        
                            with col_der_acad:
                                # --- 4. DIPLOMADOS ---
                                st.markdown("<h4 style='color: #FFD700; font-weight: bold; margin-top: 15px; border-bottom: 2px solid #FFD700; padding-bottom: 5px;'>🏅 Diplomados</h4>", unsafe_allow_html=True)
                                if df_diplo.empty:
                                    st.markdown("<p style='color:#DDDDDD;'>No registrados.</p>", unsafe_allow_html=True)
                                else:
                                    for _, row in df_diplo.iterrows():
                                        inst = get_val(row, ['institucion educativa', 'INSTITUCION EDUCATIVA', 'institución educativa'])
                                        mencion = get_val(row, ['mencion (especialidad / carrera / etc)', 'MENCION (ESPECIALIDAD / CARRERA / ETC)', 'mención'])
                                        anio = get_val(row, ['AÑO', 'año'])
                                        horas = get_val(row, ['horas academicas', 'HORAS ACADEMICAS', 'horas académicas'])
                        
                                        st.markdown(f"""
                                        <div style='background-color: #FFFFFF; padding: 15px; border-radius: 8px; border: 1px solid #CCCCCC; border-left: 6px solid #03A9F4; margin-bottom: 10px;'>
                                            <div style='margin-bottom: 5px; color: #000000; font-size: 1em; font-weight: bold;'>{mencion}</div>
                                            <div style='margin: 2px 0; color: #000000;'><strong>Institución:</strong> {inst}</div>
                                            <div style='margin: 2px 0; color: #000000;'><strong>Horas Ac.:</strong> {horas} hrs | <strong>Año:</strong> {anio}</div>
                                        </div>
                                        """, unsafe_allow_html=True)
                        
                                # --- 5. CURSOS ---
                                st.markdown("<h4 style='color: #FFD700; font-weight: bold; margin-top: 15px; border-bottom: 2px solid #FFD700; padding-bottom: 5px;'>📚 Cursos</h4>", unsafe_allow_html=True)
                                if df_cursos.empty:
                                    st.markdown("<p style='color:#DDDDDD;'>No registrados.</p>", unsafe_allow_html=True)
                                else:
                                    for _, row in df_cursos.iterrows():
                                        inst = get_val(row, ['institucion educativa', 'INSTITUCION EDUCATIVA', 'institución educativa'])
                                        mencion = get_val(row, ['mencion (especialidad / carrera / etc)', 'MENCION (ESPECIALIDAD / CARRERA / ETC)', 'mención'])
                                        anio = get_val(row, ['AÑO', 'año'])
                                        horas = get_val(row, ['horas academicas', 'HORAS ACADEMICAS', 'horas académicas'])
                        
                                        st.markdown(f"""
                                        <div style='background-color: #FFFFFF; padding: 15px; border-radius: 8px; border: 1px solid #CCCCCC; border-left: 6px solid #4CAF50; margin-bottom: 10px;'>
                                            <div style='margin-bottom: 5px; color: #000000; font-size: 1em; font-weight: bold;'>{mencion}</div>
                                            <div style='margin: 2px 0; color: #000000;'><strong>Institución:</strong> {inst}</div>
                                            <div style='margin: 2px 0; color: #000000;'><strong>Horas Ac.:</strong> {horas} hrs | <strong>Año:</strong> {anio}</div>
                                        </div>
                                        """, unsafe_allow_html=True)
                        
                            st.markdown("<br>", unsafe_allow_html=True)
                        
                            # =========================================================
                            # SECCIÓN: FORMULARIO PARA REGISTRAR NUEVOS ESTUDIOS
                            # =========================================================
                            with st.expander("➕ Clic aquí para Agregar Nueva Formación Académica"):
                                with st.form(key="form_nuevo_estudio", clear_on_submit=True):
                                    st.markdown("##### 📝 Registrar Nuevo Estudio")
                                    f_col1, f_col2 = st.columns(2)
                        
                                    with f_col1:
                                        nuevo_tipo = st.selectbox("Tipo de Estudio *", [
                                            "Grado / Título", 
                                            "Estudios Sin Grado / Inconclusos", 
                                            "Especialización", 
                                            "Diplomado", 
                                            "Curso"
                                        ])
                                        nueva_inst = st.text_input("Institución Educativa *")
                                        nueva_mencion = st.text_input("Mención (Especialidad / Carrera / Tema) *")
                        
                                    with f_col2:
                                        nuevo_grado = st.text_input("Grado o Título Obtenido (si aplica)")
                                        nuevo_estado = st.selectbox("Estado", ["Concluido", "En Curso", "Inconcluso"])
                        
                                        sub_c1, sub_c2 = st.columns(2)
                                        with sub_c1:
                                            nuevo_anio = st.text_input("Año", value="")
                                        with sub_c2:
                                            nuevas_horas = st.text_input("Horas Académicas", value="")
                        
                                    btn_guardar = st.form_submit_button("💾 Guardar Registro")
                        
                                    if btn_guardar:
                                        if not nueva_inst.strip() or not nueva_mencion.strip():
                                            st.warning("⚠️ Por favor completa los campos obligatorios (*).")
                                        else:
                                            nuevo_registro = {
                                                "dni": str(dni_buscado),
                                                "TIPO DE ESTUDIO": nuevo_tipo,
                                                "INSTITUCION EDUCATIVA": nueva_inst,
                                                "MENCION (ESPECIALIDAD / CARRERA / ETC)": nueva_mencion,
                                                "GRADO O TITULO OBTENIDO": nuevo_grado,
                                                "ESTADO": nuevo_estado,
                                                "AÑO": nuevo_anio,
                                                "HORAS ACADEMICAS": nuevas_horas
                                            }
                                            st.success("✅ ¡Formación académica registrada correctamente!")
                                            st.rerun()
                        
                            # =========================================================
                            # SECCIÓN: TABLA DE SELECCIÓN PARA EDITAR / ELIMINAR
                            # =========================================================
                            with st.expander("⚙️ Clic aquí para Editar o Eliminar Formación Académica"):
                                st.markdown("<span style='color:#A0A0A0; font-size:14px;'>Activa la casilla <b>SEL</b> en la tabla de abajo para modificar o eliminar un registro.</span>", unsafe_allow_html=True)
                        
                                if h_name in dfs and not dfs[h_name].empty and "dni" in dfs[h_name].columns:
                                    df_fa = dfs[h_name][dfs[h_name]["dni"].astype(str) == str(dni_buscado)].copy()
                                else:
                                    df_fa = pd.DataFrame()
                        
                                if not df_fa.empty:
                                    if "SEL" not in df_fa.columns:
                                        df_fa.insert(0, "SEL", False)
                        
                                    ed = st.data_editor(
                                        df_fa,
                                        hide_index=True,
                                        use_container_width=True,
                                        disabled=[c for c in df_fa.columns if c != "SEL"],
                                        key="editor_form_acad"
                                    )
                                    sel = ed[ed["SEL"] == True] if "SEL" in ed.columns else pd.DataFrame()
                                else:
                                    st.info("No hay registros para mostrar.")
                                    sel = pd.DataFrame()
                        
                        # =========================================================
                        # PESTAÑAS ESTÁNDAR (TABLA INTERACTIVA GENERAL / DEFAULT)
                        # =========================================================
                        else:
                            vst = c_df.copy() if not c_df.empty else pd.DataFrame()
                            if not vst.empty:
                                if "SEL" not in vst.columns:
                                    vst.insert(0, "SEL", False)
                        
                                conf = col_conf if 'col_conf' in locals() else {}
                                columnas_basura = ["DNI", "FECHA DE INICIO", "FECHA DE FIN", "DIAS GENERADOS", "SALDO"]
                                for col in columnas_basura:
                                    if col in vst.columns:
                                        conf[col] = None
                        
                                cols_importantes = ["SEL", "PERIODO", "F_INICIO", "F_FIN", "DIAS GOZADOS"]
                                cols_finales = [c for c in cols_importantes if c in vst.columns] + [c for c in vst.columns if c not in cols_importantes]
                                cols_finales = list(dict.fromkeys(cols_finales))  # Remover duplicados
                                vst = vst[cols_finales]
                        
                                st.markdown("<p style='color:#DDDDDD;'>Seleccione un registro con la casilla <b>SEL</b> para realizar cambios.</p>", unsafe_allow_html=True)
                                ed = st.data_editor(vst, hide_index=True, use_container_width=True, column_config=conf, key=f"ed_{h_name}")
                                sel = ed[ed["SEL"] == True]
                            else:
                                st.info(f"Sin información registrada en {h_name}.")
                        # ==========================================
                        # PESTAÑA: DATOS FAMILIARES
                        # ==========================================
                        if h_name == "DATOS FAMILIARES":
                            st.markdown("<h3 style='color: #FFD700; margin-bottom: 20px;'>👨‍👩‍👧‍👦 Datos Familiares</h3>", unsafe_allow_html=True)
                            
                            # --- DEFINICIÓN DE VST (Se inicializa la variable de los familiares del trabajador) ---
                            vst = c_df.copy()
                        
                            # --- 1. BUSCAR LA DIRECCIÓN DEL TRABAJADOR ---
                            dir_trabajador = ""
                            if not dfs["DATOS GENERALES"].empty:
                                df_gen = dfs["DATOS GENERALES"]
                                datos_trabajador = df_gen[df_gen["dni"].astype(str) == str(dni_buscado)]
                                if not datos_trabajador.empty:
                                    for col in datos_trabajador.columns:
                                        if str(col).strip().upper() == "DIRECCION":
                                            val = datos_trabajador.iloc[0][col]
                                            if pd.notna(val) and str(val).strip() != "":
                                                dir_trabajador = str(val)
                                            break
                        
                            # --- 2. MOSTRAR FAMILIARES REGISTRADOS ---
                            st.markdown("<h4 style='color: #FFD700; border-bottom: 2px solid #FFD700; padding-bottom: 5px;'>📋 Familiares Registrados</h4>", unsafe_allow_html=True)
                            
                            def get_fam_val(r, col_name):
                                for col in r.index:
                                    if str(col).strip().lower() == col_name.lower():
                                        val = r[col]
                                        if pd.notna(val) and str(val).strip() != "":
                                            return str(val)
                                return "-"
                        
                            if len(vst) == 0:
                                st.markdown("<p style='color:#DDDDDD;'>No hay familiares registrados aún.</p>", unsafe_allow_html=True)
                            else:
                                for idx, row in vst.iterrows():
                                    f_dni = get_fam_val(row, "dni familiar")
                                    if f_dni == "-": 
                                        f_dni = get_fam_val(row, "dni_familiar")
                                    f_parentesco = get_fam_val(row, "parentesco")
                                    f_nombres = get_fam_val(row, "nombres y apellidos")
                                    f_edad = get_fam_val(row, "edad")
                                    f_estado = get_fam_val(row, "estado")
                                    f_celular = get_fam_val(row, "celular")
                                    f_correo = get_fam_val(row, "correo")
                                    f_domicilio = get_fam_val(row, "domicilio")
                                    f_sit_acad = get_fam_val(row, "situacion academica")
                                    f_emergencia = get_fam_val(row, "contacto emergencia").lower()
                                    
                                    badge_emergencia = "<span style='color: #FF5252; font-size: 0.9em;'>🚨 <b>CONTACTO DE EMERGENCIA</b></span>" if f_emergencia in ["sí", "si", "true", "1"] else ""
                                    
                                    st.markdown(f"""
                                    <div style='background-color: #FFFFFF; padding: 15px; border-radius: 8px; border: 1px solid #CCCCCC; border-left: 6px solid #2196F3; margin-bottom: 10px; color: #000000;'>
                                        <div style='margin-bottom: 10px; font-size: 1.1em; font-weight: bold; border-bottom: 1px solid #EEEEEE; padding-bottom: 5px;'>
                                            {f_nombres} <span style='color: #666666; font-size: 0.9em;'>({f_parentesco})</span> {badge_emergencia}
                                        </div>
                                        <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 0.95em;'>
                                            <div><strong>DNI:</strong> {f_dni}</div>
                                            <div><strong>Edad:</strong> {f_edad} años</div>
                                            <div><strong>Estado:</strong> {f_estado}</div>
                                            <div><strong>Celular:</strong> {f_celular}</div>
                                            <div><strong>Correo:</strong> {f_correo}</div>
                                            <div><strong>Sit. Académica:</strong> {f_sit_acad}</div>
                                            <div style='grid-column: span 2;'><strong>Domicilio:</strong> {f_domicilio}</div>
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)
                            
                            st.markdown("<br>", unsafe_allow_html=True)
                            
                            # --- 3. TABLA DESPLEGABLE PARA EDICIÓN ---
                            with st.expander("⚙️ Clic aquí para Editar o Eliminar un Familiar"):
                                st.markdown("<p style='color:#DDDDDD;'>Activa la casilla <b>SEL</b> en la tabla de abajo para modificar o eliminar un registro.</p>", unsafe_allow_html=True)
                                
                                if dir_trabajador:
                                    st.info(f"💡 **Tip para la edición:** Si el familiar vive con el trabajador, simplemente copia y pega esta dirección en la tabla: \n**{dir_trabajador}**")
                                    
                                st.markdown("""<style>[data-testid="stDataEditor"] { border: 2px solid #FFD700 !important; border-radius: 8px !important; }</style>""", unsafe_allow_html=True)
                                
                                # Garantizar que la columna SEL existe en vst
                                vst_editor = vst.copy()
                                if "SEL" not in vst_editor.columns:
                                    vst_editor.insert(0, "SEL", False)
                                    
                                ed = st.data_editor(vst_editor, hide_index=True, use_container_width=True, key=f"ed_{h_name}_oculta")
                                sel_fam = ed[ed["SEL"] == True]
                            
                            # --- 4. FORMULARIO DENTRO DE "NUEVO REGISTRO" ---
                            st.markdown("<br>", unsafe_allow_html=True)
                            with st.expander("➕ NUEVO REGISTRO"):
                                st.markdown("<p style='color:#DDDDDD; font-style: italic;'>Rellena los datos para agregar un familiar.</p>", unsafe_allow_html=True)
                                col_f1, col_f2 = st.columns(2)
                                
                                with col_f1:
                                    parentesco = st.selectbox("Parentesco", ["Cónyuge / Conviviente", "Hijo(a)", "Madre", "Padre", "Hermano(a)", "Familiar Adicional (Otros)"])
                                    dni_fam = st.text_input("DNI del Familiar", max_chars=8)
                                    
                                    if dni_fam and len(dni_fam) >= 8:
                                        if not dfs["DATOS GENERALES"].empty:
                                            es_trabajador = dfs["DATOS GENERALES"][dfs["DATOS GENERALES"]["dni"].astype(str) == str(dni_fam)]
                                            if not es_trabajador.empty:
                                                nombre_vinculo = es_trabajador.iloc[0].get("apellidos y nombres", "Trabajador")
                                                st.success(f"🔗 ¡Vínculo detectado! Este familiar es trabajador activo: **{nombre_vinculo}**")
                                    
                                    nombres_fam = st.text_input("Apellidos y Nombres")
                                    f_nac_fam = st.date_input("Fecha de Nacimiento", min_value=date(1920, 1, 1), max_value=date.today())
                                    hoy = date.today()
                                    edad_fam = hoy.year - f_nac_fam.year - ((hoy.month, hoy.day) < (f_nac_fam.month, f_nac_fam.day))
                                    st.info(f"🎂 Edad calculada: **{edad_fam} años**")
                                
                                with col_f2:
                                    estado_fam = st.selectbox("Estado", ["Vivo", "Fallecido", "Otra condición"])
                                    
                                    if estado_fam == "Vivo":
                                        cel_fam = st.text_input("Celular")
                                        correo_fam = st.text_input("Correo Electrónico")
                                        st.markdown("---")
                                        vive_juntos = st.checkbox("🏠 Vive con el trabajador")
                                        
                                        if vive_juntos:
                                            domicilio_fam = st.text_input("Domicilio del familiar", value=dir_trabajador, key="domicilio_juntos")
                                            if not dir_trabajador:
                                                st.warning("⚠️ Ojo: El trabajador no tiene una dirección registrada en su pestaña de Datos Generales.")
                                        else:
                                            domicilio_fam = st.text_input("Domicilio del familiar", value="", key="domicilio_separado")
                                    else:
                                        cel_fam = "-"
                                        correo_fam = "-"
                                        domicilio_fam = "-"
                                        vive_juntos = False
                                    
                                    sit_acad_fam = st.selectbox("Situación Académica", [
                                        "Ninguna / No aplica",
                                        "Estudiando Primaria", "Estudiando Secundaria", "Estudiando Superior",
                                        "Estudios Concluidos Primaria", "Estudios Concluidos Secundaria", "Estudios Concluidos Superior"
                                    ])
                                    contacto_emergencia = st.checkbox("🚨 Es Contacto de Emergencia Principal")
                                
                                if st.button("💾 Guardar Familiar", type="primary"):
                                    if not dni_fam or not nombres_fam:
                                        st.error("⚠️ El DNI y los Nombres son obligatorios.")
                                    else:
                                        new_row = {
                                            "dni": str(dni_buscado),
                                            "dni familiar": str(dni_fam),
                                            "parentesco": parentesco,
                                            "nombres y apellidos": nombres_fam,
                                            "fecha de nacimiento": str(f_nac_fam),
                                            "edad": edad_fam,
                                            "domicilio": domicilio_fam,
                                            "estado": estado_fam,
                                            "celular": cel_fam,
                                            "correo": correo_fam,
                                            "situacion academica": sit_acad_fam,
                                            "contacto emergencia": "Sí" if contacto_emergencia else "No"
                                        }
                                        
                                        if not dfs[h_name].empty and "id" in dfs[h_name].columns:
                                            new_row["id"] = dfs[h_name]["id"].max() + 1
                                        elif "id" in dfs[h_name].columns:
                                            new_row["id"] = 1
                                            
                                        dfs[h_name] = pd.concat([dfs[h_name], pd.DataFrame([new_row])], ignore_index=True)
                                        save_data(dfs)
                                        st.success("✅ Familiar guardado correctamente.")
                                        st.rerun()
                        
                        # ==========================================
                        # LÓGICA DE VACACIONES E IMPRESIÓN DE PAPELETA
                        # ==========================================
                        elif h_name == "VACACIONES":
                            vst_vac = vst.copy()
                            if "SEL" not in vst_vac.columns:
                                vst_vac.insert(0, "SEL", False)
                            
                            sel_vac = vst_vac[vst_vac["SEL"] == True]
                        
                            if not sel_vac.empty:
                                st.markdown("---")
                                current_cargo = "TRABAJADOR"
                                f_ingreso_val = ""
                                df_c_data = dfs["CONTRATOS"][dfs["CONTRATOS"]["dni"] == dni_buscado]
                                
                                if not df_c_data.empty:
                                    try:
                                        last_contract = df_c_data.assign(f_fin_dt=pd.to_datetime(df_c_data['f_fin'], errors='coerce')).sort_values('f_fin_dt').iloc[-1]
                                        current_cargo = last_contract.get("cargo", "TRABAJADOR")
                                        
                                        df_planilla = df_c_data[df_c_data["tipo contrato"].astype(str).str.lower().str.contains("planilla", na=False)]
                                        if not df_planilla.empty:
                                            f_min = pd.to_datetime(df_planilla['f_inicio'], errors='coerce').min()
                                            if pd.notnull(f_min): 
                                                f_ingreso_val = f_min.date()
                                    except Exception as e:
                                        st.warning(f"No se pudieron consolidar los contratos: {e}")
                        
                                r_sel = sel_vac.iloc[0]
                                
                                cols_per = [c for c in r_sel.index if "PERIODO" in str(c).upper()]
                                cols_ini = [c for c in r_sel.index if "INICIO" in str(c).upper()]
                                cols_fin = [c for c in r_sel.index if "FIN" in str(c).upper()]
                                cols_dias = [c for c in r_sel.index if "GOZADOS" in str(c).upper()]
                        
                                def get_valid_val(cols):
                                    for c in cols:
                                        val = r_sel.get(c)
                                        if pd.notnull(val) and str(val).strip() not in ["", "NaT", "None"]:
                                            return val
                                    return None
                        
                                p_papeleta = str(get_valid_val(cols_per) or "")
                                fi_papeleta_raw = get_valid_val(cols_ini)
                                ff_papeleta_raw = get_valid_val(cols_fin)
                                dg_papeleta_raw = get_valid_val(cols_dias) or 0
                                
                                try:
                                    fi_papeleta = pd.to_datetime(fi_papeleta_raw).date() if fi_papeleta_raw else None
                                except Exception:
                                    fi_papeleta = None
                                    
                                try:
                                    ff_papeleta = pd.to_datetime(ff_papeleta_raw).date() if ff_papeleta_raw else None
                                except Exception:
                                    ff_papeleta = None
                        
                                try:
                                    dg_papeleta = int(float(dg_papeleta_raw))
                                except (ValueError, TypeError):
                                    dg_papeleta = 0
                        
                                if st.button(f"📄 Generar Papeleta de Impresión (Periodo {p_papeleta})", key="btn_print_vaca_tab", use_container_width=False):
                                    if fi_papeleta is None or ff_papeleta is None:
                                        st.error(f"⚠️ Aún no se detectan fechas válidas. Inicio extraído: '{fi_papeleta_raw}' | Fin extraído: '{ff_papeleta_raw}'")
                                    else:
                                        papeleta_word = gen_papeleta_vac(ape_c, nom_p_c, dni_buscado, current_cargo, f_ingreso_val, p_papeleta, fi_papeleta, ff_papeleta, dg_papeleta)
                                        if papeleta_word:
                                            st.markdown("""<style>[data-testid="stDownloadButton"] button { background-color: #FFD700 !important; color: #4A0000 !important; font-weight: bold !important; border: 2px solid #4A0000 !important; width: 100% !important; }</style>""", unsafe_allow_html=True)
                                            st.download_button(
                                                label=f"⬇️ Descargar Papeleta - {nom_c}.docx",
                                                data=papeleta_word,
                                                file_name=f"Papeleta_{dni_buscado}_{p_papeleta}.docx",
                                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                                key="dl_papeleta_tab"
                                            )
                                st.markdown("---")
                        
                        # ==========================================
                        # GESTIÓN GLOBAL PARA OTRAS PESTAÑAS Y FORMULARIO NUEVO REGISTRO
                        # ==========================================
                        if not es_lector:
                            if h_name not in dfs:
                                st.error(f"⚠️ Error crítico: No se pudo cargar la pestaña '{h_name}'. Por favor, entra al Google Sheets y elimina las columnas duplicadas.")
                            else:
                                cols_reales = [c for c in dfs[h_name].columns if c.lower() not in ["id", "dni", "apellidos y nombres", "apellidos", "nombres"]]
                                df_filtro = dfs[h_name][dfs[h_name]["dni"] == dni_buscado] if not dfs[h_name].empty else pd.DataFrame()
                        
                                if h_name == "DATOS GENERALES" and len(df_filtro) > 0:
                                    st.info("📌 Los datos generales ya están registrados. Selecciona el registro en la tabla de arriba para editarlos.")
                                elif h_name == "DATOS FAMILIARES":
                                    pass  # Ya se manejó arriba en su respectiva sección
                                else:
                                    with st.expander("➕ Nuevo Registro"):
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
                                                f_ini_val = st.date_input("Fecha de Salida (Inicio)", min_value=date(1950, 1, 1), max_value=date(2100, 12, 31))
                                            with col_f2:
                                                f_fin_val = st.date_input("Fecha de Retorno (Último día)", min_value=date(1950, 1, 1), max_value=date(2100, 12, 31))
                        
                                            dias_gozar_calc = 0
                                            if f_fin_val >= f_ini_val:
                                                dias_gozar_calc = (f_fin_val - f_ini_val).days + 1
                                            
                                            gen_periodo = dict_generados.get(sel_periodo, 0)
                                            saldo_previo = dict_saldo_actual.get(sel_periodo, 0)
                                            nuevo_saldo = saldo_previo - dias_gozar_calc
                        
                                            if nuevo_saldo < 0:
                                                txt_saldo = f":red[{nuevo_saldo:.2f} (¡Saldo Negativo!)]"
                                            elif nuevo_saldo == 0:
                                                txt_saldo = f"{nuevo_saldo:.2f}"
                                            else:
                                                txt_saldo = f":green[{nuevo_saldo:.2f}]"
                        
                                            st.markdown(f"""
                                            **Resumen:**
                                            * **Días a Gozar (Calculado):** {dias_gozar_calc}
                                            * **Saldo Restante:** {txt_saldo}
                                            """)
                                            
                                            if st.button("💾 Guardar Registro de Vacaciones", type="primary", use_container_width=False):
                                                if dias_gozar_calc <= 0:
                                                    st.error("⚠️ La Fecha de Fin debe ser igual o posterior a la Fecha de Inicio.")
                                                else:
                                                    new_row = {
                                                        "dni": dni_buscado, 
                                                        "periodo": sel_periodo, 
                                                        "f inicio": f_ini_val, 
                                                        "f fin": f_fin_val, 
                                                        "dias gozados": dias_gozar_calc
                                                    }
                                                    
                                                    if not dfs[h_name].empty and "id" in dfs[h_name].columns:
                                                        new_row["id"] = dfs[h_name]["id"].max() + 1
                                                    elif "id" in dfs[h_name].columns:
                                                        new_row["id"] = 1
                                                    
                                                    dfs[h_name] = pd.concat([dfs[h_name], pd.DataFrame([new_row])], ignore_index=True)
                                                    save_data(dfs)
                                                    st.session_state['just_saved_vacation'] = new_row
                                                    st.success("✅ Registro guardado correctamente.")
                                                    st.rerun()
                        
                                        else:
                                            # ==========================================
                                            # FORMULARIO GENÉRICO (Para otras pestañas)
                                            # ==========================================
                                            st.markdown(f"<div style='font-size: 1.3em; font-weight: bold; color: white; background-color: #333333; padding: 10px; border-radius: 8px; margin-bottom: 15px;'>➕ Registrar en {h_name}</div>", unsafe_allow_html=True)
                                            
                                            new_data = {}
                                            for col in cols_reales:
                                                col_lower = str(col).strip().lower()
                                                key_input = f"inp_{h_name}_{col}"
                                                
                                                if "fecha" in col_lower or col_lower.startswith("f_") or col_lower.startswith("f "):
                                                    new_data[col] = st.date_input(f"{col.title()}", min_value=date(1950, 1, 1), max_value=date(2100, 12, 31), key=key_input)
                                                elif any(k in col_lower for k in ["monto", "precio", "sueldo", "remuneracion"]):
                                                    new_data[col] = st.number_input(f"{col.title()}", min_value=0.0, value=0.0, step=10.0, key=key_input)
                                                elif any(k in col_lower for k in ["observacion", "detalle", "descripcion"]):
                                                    new_data[col] = st.text_area(f"{col.title()}", key=key_input)
                                                else:
                                                    new_data[col] = st.text_input(f"{col.title()}", key=key_input)
                        
                                            if st.button(f"💾 Guardar Registro en {h_name}", type="primary", use_container_width=False):
                                                new_row = {"dni": str(dni_buscado)}
                                                new_row.update(new_data)
                        
                                                if not dfs[h_name].empty and "id" in dfs[h_name].columns:
                                                    new_row["id"] = dfs[h_name]["id"].max() + 1
                                                elif "id" in dfs[h_name].columns:
                                                    new_row["id"] = 1
                        
                                                dfs[h_name] = pd.concat([dfs[h_name], pd.DataFrame([new_row])], ignore_index=True)
                                                save_data(dfs)
                                                st.cache_data.clear()
                                                st.success(f"✅ Registro guardado en {h_name} correctamente.")
                                                st.rerun()
                        # ==========================================
                        # ACCIONES GLOBALES: MODIFICAR / ELIMINAR
                        # ==========================================
                        if 'ed' in locals() and not ed.empty and "SEL" in ed.columns:
                            sel_rows = ed[ed["SEL"] == True]
                            if not sel_rows.empty:
                                st.markdown("---")
                                st.markdown("### 🛠️ Acciones sobre el registro seleccionado")
                                col_act1, col_act2 = st.columns(2)
                                
                                with col_act1:
                                    if st.button("✏️ Guardar Cambios Editados en Tabla", type="secondary", use_container_width=True):
                                        # Actualizar DataFrame original con las filas editadas
                                        for idx, row in ed.iterrows():
                                            if "id" in row and pd.notna(row["id"]):
                                                mask = dfs[h_name]["id"] == row["id"]
                                                for col in ed.columns:
                                                    if col != "SEL" and col in dfs[h_name].columns:
                                                        dfs[h_name].loc[mask, col] = row[col]
                                        save_data(dfs)
                                        st.cache_data.clear()
                                        st.success("✅ Cambios actualizados con éxito.")
                                        st.rerun()
                        
                                with col_act2:
                                    if st.button("🗑️ Eliminar Registro Seleccionado", type="primary", use_container_width=True):
                                        ids_to_delete = sel_rows["id"].tolist() if "id" in sel_rows.columns else []
                                        if ids_to_delete:
                                            dfs[h_name] = dfs[h_name][~dfs[h_name]["id"].isin(ids_to_delete)]
                                            save_data(dfs)
                                            st.cache_data.clear()
                                            st.warning("🗑️ Registro eliminado correctamente.")
                                            st.rerun()
                                        else:
                                            st.error("⚠️ No se encontró la columna 'id' para ejecutar la eliminación.")
                        
                                # ==========================================
                                # COLUMNA B: TABLA INTERACTIVA Y EDICIÓN
                                # ==========================================
                                if 'col_b' in locals():
                                    with col_b:
                                        # Delegación del renderizado y edición al módulo externo mod_editor
                                        mod_editor.mostrar_editor(dfs, save_data, h_name, sel, cols_reales)
                        
                            # ==========================================
                            # PIE DE PÁGINA Y ESTADO DEL EXPEDIENTE
                            # ==========================================
                            st.markdown("---")
                            st.caption(f"📌 **Expediente activo:** DNI `{dni_buscado}` | Datos sincronizados correctamente con el almacenamiento local.")
                        
                        elif 'dni_buscado' in locals() and dni_buscado and m == "📁 Expediente":
                            st.warning(f"⚠️ No se encontró ningún expediente registrado con el DNI: **{dni_buscado}**")

# ==========================================
# --- SECCIÓN REGISTRO Y NÓMINA Y MÓDULOS ---
# ==========================================

# Resguardo de seguridad para evitar NameError si las variables no se declararon antes
m = m if 'm' in locals() or 'm' in globals() else st.session_state.get("m", st.session_state.get("menu", ""))
es_lector = es_lector if 'es_lector' in locals() or 'es_lector' in globals() else st.session_state.get("es_lector", False)

if m == "➕ Registro" and not es_lector:
    import mod_registro
    mod_registro.mostrar(dfs, save_data)
    
elif m == "📊 Nómina General":
    mod_nomina.mostrar(dfs, save_data)
    
# ==========================================
# MÓDULO: ESTRUCTURA Y PUESTOS (MOF)
# ==========================================
elif m == "🏢 Estructura":
    mod_estructura.mostrar(dfs)    
    
# ==========================================
# MÓDULO: REPORTE GENERAL
# ==========================================
elif m == "Reporte General": 
    mod_reportegeneral.mostrar(dfs)

# ==========================================
# MÓDULO: REPORTE DE SALDO DE VACACIONES
# ==========================================
elif m == "Vacaciones":
    mod_vacaciones.mostrar(dfs)

# ==========================================
# MÓDULO: CUMPLEAÑEROS
# ==========================================
elif m == "Cumpleañeros":
    mod_cumpleanos.mostrar(dfs)   
    
# ==========================================
# MÓDULO: VENCIMIENTO DE CONTRATOS
# ==========================================
elif m == "Vencimientos":
    mod_vencimientos.mostrar(dfs)

# ==========================================
# MÓDULO: DASHBOARD DE DESEMPEÑO
# ==========================================
elif m == "📈 Dashboard Desempeño":
    import mod_reportes
    mod_reportes.mostrar(dfs)

# ==========================================
# MÓDULO: GESTOR DE EVALUACIONES
# ==========================================
elif m == "📋 Evaluaciones":
    mod_gestor_evaluaciones.mostrar(dfs, save_data)

# ==========================================
# MÓDULO: USUARIOS Y SEGURIDAD
# ==========================================
elif m == "🔐 Usuarios y Seguridad":
    mod_usuarios.mostrar(dfs, save_data)

# ==========================================
# MÓDULO: HORARIOS ADMINISTRATIVOS
# ==========================================
elif m == "⏰ Horarios Administrativos":
    import importlib
    import mod_horarios_admin
    
    try:
        importlib.reload(mod_horarios_admin)  # Fuerza la lectura del código actualizado
    except Exception as e:
        st.warning(f"Aviso: No se pudo recargar el módulo dinámicamente ({e}). Se ejecutará la versión en memoria.")
        
    mod_horarios_admin.mostrar(dfs, save_data)
