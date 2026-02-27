# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
from datetime import date
from io import BytesIO
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

st.set_page_config(page_title="Gestión Roosevelt", page_icon="🎓", layout="wide")
# ==========================================
# 1. CONFIGURACIÓN Y CONSTANTES
# ==========================================
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

# ==========================================
# 2. FUNCIONES DE DATOS Y WORD
# ==========================================
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

# ==========================================
# 3. ESTILOS CSS CORREGIDOS
# ==========================================
st.markdown("""
<style>
    /* Fondo general */
    .stApp { background-color: #4a0000 !important; }
    
    /* SIDEBAR */
    [data-testid="stSidebar"] { background-color: #4a0000 !important; }
    [data-testid="stSidebar"] h3, [data-testid="stSidebar"] label, [data-testid="stSidebar"] p {
        color: #FFD700 !important; font-weight: bold !important;
    }
    
    /* Logo con recuadro amarillo */
    [data-testid="stSidebar"] [data-testid="stImage"] {
        background-color: #FFF9C4 !important;
        border: 4px solid #FFD700 !important;
        border-radius: 15px !important;
        padding: 10px !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.3) !important;
    }
    
    /* TODOS LOS BOTONES (Sidebar, Guardar, Actualizar) */
    div.stButton > button, [data-testid="stFormSubmitButton"] > button {
        background-color: #FFD700 !important;
        color: #4a0000 !important; /* TEXTO GUINDO OSCURO VISTOSO */
        border-radius: 10px !important;
        border: 2px solid #FFFFFF !important;
        font-weight: bold !important;
        font-size: 16px !important;
    }
    div.stButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover {
        background-color: #ffffff !important;
        color: #4a0000 !important;
        border-color: #FFD700 !important;
    }

    /* Pestañas (Tabs) visibles */
    [data-testid="stTabs"] button { color: #FFFFFF !important; font-weight: bold !important; font-size: 16px !important; }
    [data-testid="stTabs"] button[aria-selected="true"] { color: #FFD700 !important; border-bottom-color: #FFD700 !important; }

    /* Expanders (Opciones de Agregar, Editar, Eliminar) */
    [data-testid="stExpander"] details { background-color: #FFF9C4 !important; border: 2px solid #FFD700 !important; border-radius: 10px !important; overflow: hidden !important; }
    [data-testid="stExpander"] summary { background-color: #FFD700 !important; padding: 10px !important; }
    [data-testid="stExpander"] summary p { color: #4a0000 !important; font-weight: bold !important; font-size: 16px !important; }

    /* TABLAS Y DATA EDITORS (Forzando las cabeceras a amarillo) */
    [data-testid="stDataEditor"], [data-testid="stTable"], .stTable { background-color: white !important; border-radius: 10px !important; overflow: hidden !important; }
    /* Cabeceras de Data Editor (React Data Grid) */
    [data-testid="stDataEditor"] .react-grid-HeaderCell { background-color: #FFF9C4 !important; }
    [data-testid="stDataEditor"] .react-grid-HeaderCell span { color: #4a0000 !important; font-weight: bold !important; text-transform: uppercase !important; }
    /* Cabeceras de Tablas normales */
    thead tr th { background-color: #FFF9C4 !important; color: #4a0000 !important; font-weight: bold !important; text-transform: uppercase !important; border: 1px solid #f0f0f0 !important; }
    
    /* Textos generales */
    .stApp h1, .stApp h2, .stApp h3 { color: #FFD700 !important; }
    .stApp label p { color: #4a0000 !important; font-weight: bold !important; } /* Etiquetas de formulario en guindo */
    .stApp div[data-baseweb="input"] { background-color: #ffffff !important; border: 2px solid #FFD700 !important; }
    .stApp input { color: #4a0000 !important; font-weight: bold !important; }
</style>
""", unsafe_allow_html=True)
# ==========================================
# 4. LÓGICA DE DATOS Y SESIÓN
# ==========================================
if "rol" not in st.session_state:
    st.session_state.rol = None

# --- LOGIN ---
if st.session_state.rol is None:
    st.markdown('<p class="frase-talento">¡Tu talento es importante! :)</p>', unsafe_allow_html=True)

    col_logo1, col_logo2, col_logo3 = st.columns([1, 1.2, 1])
    with col_logo2:
        if os.path.exists("Logo_amarillo.png"):
            st.image("Logo_amarillo.png", use_container_width=True)
        else:
            st.warning("No se encontró el archivo Logo_amarillo.png")

    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        u = st.text_input("USUARIO")
        p = st.text_input("CONTRASEÑA", type="password")

        st.markdown('<p class="login-welcome">Bienvenido (a) al sistema de gestión de datos de los colaboradores</p>', unsafe_allow_html=True)

        if st.button("INGRESAR"):
            u_low = u.lower().strip()
            if u_low == "admin":
                st.session_state.rol = "Admin"
            elif u_low == "supervisor" and p == "123":
                st.session_state.rol = "Supervisor"
            elif u_low == "lector" and p == "123":
                st.session_state.rol = "Lector"
            else:
                st.error("Credenciales incorrectas")

            if st.session_state.rol:
                st.rerun()

# --- SISTEMA PRINCIPAL ---
else:
    dfs = load_data()
    es_lector = st.session_state.rol == "Lector"

    with st.sidebar:
        # 1. Logo superior con st.image nativo (más seguro) y tamaño reducido
        st.markdown("<br>", unsafe_allow_html=True)
        col_logo_1, col_logo_2, col_logo_3 = st.columns([1, 2, 1]) # Columnas ajustadas para hacerlo más pequeño
        with col_logo_2:
            if os.path.exists("Logo_guindo.png"):
                st.image("Logo_guindo.png", use_container_width=True)
            else:
                st.warning("Sin Logo")
        st.markdown("<br>", unsafe_allow_html=True)

        # 2. Opciones de menú
        st.markdown("### 🛠️ MENÚ PRINCIPAL")
        m = st.radio("", ["🔍 Consulta", "➕ Registro", "📊 Nómina General"], key="menu_p_unico")

        st.markdown("### 📈 REPORTES")
        r = st.radio("", ["Vencimientos", "Vacaciones", "Estadísticas"], key="menu_r_unico")
        
        st.markdown("---")

        # 3. Botón inferior
        if st.button("🚪 Cerrar Sesión", key="btn_logout"):
            st.session_state.rol = None
            st.rerun()

    col_m1, col_m2, col_m3 = st.columns([1.5, 1, 1.5])
    with col_m2:
        if os.path.exists("Logo_amarillo.png"):
            st.image("Logo_amarillo.png", use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- SECCIÓN CONSULTA ---
    if m == "🔍 Consulta":
        st.markdown("<h2 style='color: #FFD700;'>Búsqueda de Colaborador</h2>", unsafe_allow_html=True)
        dni_b = st.text_input("Ingrese DNI para consultar:").strip()

        if dni_b:
            pers = dfs["PERSONAL"][dfs["PERSONAL"]["dni"] == dni_b]
            if not pers.empty:
                nom_c = pers.iloc[0]["apellidos y nombres"]
                
                st.markdown(f"""
                    <div style='border-bottom: 2px solid #FFD700; padding-bottom: 10px; margin-bottom: 20px;'>
                        <h1 style='color: white; margin: 0;'>👤 {nom_c}</h1>
                    </div>
                """, unsafe_allow_html=True)

                t_noms = ["Datos Generales", "Exp. Laboral", "Form. Académica", "Investigación", "Datos Familiares", "Contratos", "Vacaciones", "Otros Beneficios", "Méritos/Demer.", "Evaluación", "Liquidaciones"]
                h_keys = ["DATOS GENERALES", "EXP. LABORAL", "FORM. ACADEMICA", "INVESTIGACION", "DATOS FAMILIARES", "CONTRATOS", "VACACIONES", "OTROS BENEFICIOS", "MERITOS Y DEMERITOS", "EVALUACION DEL DESEMPEÑO", "LIQUIDACIONES"]

                tabs = st.tabs(t_noms)

                for i, tab in enumerate(tabs):
                    h_name = h_keys[i]
                    with tab:
                        if "dni" in dfs[h_name].columns:
                            c_df = dfs[h_name][dfs[h_name]["dni"] == dni_b]
                        else:
                            c_df = pd.DataFrame(columns=COLUMNAS.get(h_name, []))

                        # VISTA DE TABLA EDITABLE
                        vst = c_df.copy()
                        vst.columns = [str(col).upper() for col in vst.columns] 
                        vst.insert(0, "SEL", False)

                        # Borde amarillo a la tabla interactiva
                        st.markdown("""<style>[data-testid="stDataEditor"] { border: 2px solid #FFD700 !important; border-radius: 10px !important; }</style>""", unsafe_allow_html=True)
                        
                        ed = st.data_editor(vst, hide_index=True, use_container_width=True, key=f"ed_{h_name}")
                        sel = ed[ed["SEL"] == True]

                        if not es_lector:
                            col_a, col_b = st.columns(2)
                            
                            # Identificar las columnas reales de la base de datos (ignorando id y dni)
                            cols_reales = [c for c in dfs[h_name].columns if c.lower() not in ["id", "dni", "apellidos y nombres"]]

                            # ==========================================
                            # 1. AGREGAR NUEVO DATO
                            # ==========================================
                            with col_a:
                                with st.expander("➕ Nuevo Registro"):
                                    with st.form(f"f_add_{h_name}", clear_on_submit=True):
                                        new_row = {"dni": dni_b}
                                        
                                        for col in cols_reales:
                                            # Detección de tipo de dato para el formulario
                                            if "fecha" in col.lower() or "f_" in col.lower():
                                                new_row[col] = st.date_input(col.title())
                                            elif col.lower() in ["sueldo", "días generados", "días gozados", "saldo", "edad", "monto"]:
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

                            # ==========================================
                            # 2. EDITAR / ELIMINAR DATO SELECCIONADO
                            # ==========================================
                            with col_b:
                                with st.expander("📝 Editar / Eliminar"):
                                    if not sel.empty:
                                        idx = sel.index[0]
                                        with st.form(f"f_edit_{h_name}"):
                                            edit_row = {}
                                            
                                            for col in cols_reales:
                                                val = sel.iloc[0][col.upper()]
                                                if "fecha" in col.lower() or "f_" in col.lower():
                                                    try: parsed_date = pd.to_datetime(val).date()
                                                    except: parsed_date = date.today()
                                                    edit_row[col] = st.date_input(col.title(), value=parsed_date)
                                                elif col.lower() in ["sueldo", "días generados", "días gozados", "saldo", "edad", "monto"]:
                                                    try: num_val = float(val) if pd.notnull(val) else 0.0
                                                    except: num_val = 0.0
                                                    edit_row[col] = st.number_input(col.title(), value=num_val)
                                                else:
                                                    edit_row[col] = st.text_input(col.title(), value=str(val) if pd.notnull(val) else "")
                                                    
                                            if st.form_submit_button("Actualizar Registro"):
                                                for col in cols_reales:
                                                    dfs[h_name].at[idx, col] = edit_row[col]
                                                save_data(dfs)
                                                st.rerun()
                                        
                                        if st.button("🚨 Eliminar Fila Seleccionada", key=f"del_{h_name}"):
                                            dfs[h_name] = dfs[h_name].drop(sel.index)
                                            save_data(dfs)
                                            st.rerun()
                                    else:
                                        st.info("Activa la casilla en la tabla para editar o eliminar.")
            else:
                st.error("DNI no encontrado en la base de datos.")

    elif m == "➕ Registro" and not es_lector:
        with st.form("reg_p"):
            st.write("### Alta de Nuevo Trabajador")
            d = st.text_input("DNI")
            n = st.text_input("Nombres").upper()
            l = st.text_input("Link File")

            if st.form_submit_button("Registrar"):
                if d and n:
                    dfs["PERSONAL"] = pd.concat(
                        [dfs["PERSONAL"], pd.DataFrame([{"dni": d, "apellidos y nombres": n, "link": l}])], ignore_index=True
                    )
                    save_data(dfs)
                    st.success("Registrado correctamente")

    elif m == "📊 Nómina General":
        st.markdown("<h2 style='color: #FFD700;'>👥 Trabajadores registrados en el sistema</h2>", unsafe_allow_html=True)
        
        busqueda = st.text_input("🔍 Buscar por nombre o DNI:").strip().lower()
        df_nom = dfs["PERSONAL"].copy()
        
        if busqueda:
            df_nom = df_nom[df_nom['apellidos y nombres'].str.lower().str.contains(busqueda, na=False) | df_nom['dni'].astype(str).str.contains(busqueda, na=False)]

        df_ver = df_nom.copy()
        df_ver.columns = [col.upper() for col in df_ver.columns]
        df_ver.insert(0, "SEL", False)
        
        ed_nom = st.data_editor(df_ver, hide_index=True, use_container_width=True, key="nomina_v3_blanco")

        filas_sel = ed_nom[ed_nom["SEL"] == True]
        
        if not filas_sel.empty:
            st.markdown("---")
            if st.button(f"🚨 ELIMINAR {len(filas_sel)} REGISTRO(S)", type="secondary", use_container_width=True):
                dnis = filas_sel["DNI"].astype(str).tolist()
                
                for h in dfs:
                    if 'dni' in dfs[h].columns:
                        dfs[h] = dfs[h][~dfs[h]['dni'].astype(str).isin(dnis)]
                
                save_data(dfs)
                st.success("Registros eliminados correctamente del sistema y del Excel.")
                st.rerun()








