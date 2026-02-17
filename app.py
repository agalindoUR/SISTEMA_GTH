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

# --- 2. FUNCIONES ---
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

# --- 3. DISEÑO Y LOGIN ---
st.set_page_config(page_title="GTH Roosevelt", layout="wide")
st.markdown("""
    <style>
    /* 1. FONDO PRINCIPAL Y LOGIN */
    .stApp { 
        background: linear-gradient(135deg, #4a0000 0%, #800000 100%); 
    }
    .login-welcome { 
        color: #FFD700 !important; 
        text-align: center; 
        font-size: 19px !important; 
        font-weight: bold !important;
        display: block;
        margin-top: 15px;
    }

    /* 2. BARRA LATERAL (SIDEBAR) */
    [data-testid="stSidebar"] {
        background-color: #C5A059 !important; /* Dorado oscuro */
    }
    /* Color Guinda para TODO el texto del sidebar */
    [data-testid="stSidebar"] h3, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] [data-testid="stRadioButton"] label span {
        color: #4a0000 !important;
        font-weight: bold !important;
    }
    [data-testid="stSidebar"] hr {
        border-color: #4a0000 !important;
    }

    /* 3. ÁREA DE TRABAJO (DERECHA) */
    .stApp:not([data-testid="stSidebar"]) .stForm h3, 
    .stApp:not([data-testid="stSidebar"]) .stMarkdown h3 {
        color: #D3D3D3 !important; /* Plomo claro títulos */
        border-bottom: 2px solid #FFD700;
        padding-bottom: 5px;
    }
    .stApp:not([data-testid="stSidebar"]) label p {
        color: white !important; /* Etiquetas blancas */
    }

    /* 4. BOTONES */
    div.stButton > button {
        background-color: #FFD700 !important;
        color: #4a0000 !important;
        font-weight: bold !important;
        border-radius: 10px !important;
        width: 100% !important;
        border: none !important;
        height: 3em !important;
    }
    div.stButton > button:hover {
        background-color: #f0f0f0 !important;
    }

   /* 5. TABLAS (FORZAR ENCABEZADO PLOMO Y MAYÚSCULAS) */
    /* Este bloque apunta a todos los tipos de tablas de Streamlit */
    
    /* 5.1 Para st.table (tablas estáticas) */
    [data-testid="stTable"] thead tr th {
        background-color: #D3D3D3 !important; /* Plomo Claro */
        text-transform: uppercase !important; /* MAYÚSCULAS */
        color: #4a0000 !important; /* Letras Guindas */
        font-weight: bold !important;
        text-align: center !important;
    }

    /* 5.2 Para st.dataframe (tablas interactivas modernas) */
    [data-testid="stDataFrame"] div[data-testid="stTable"] thead tr th,
    div[data-cell-contents="true"] {
        text-transform: uppercase !important;
    }

    /* 5.3 Selector universal para cualquier celda de encabezado */
    th {
        background-color: #D3D3D3 !important;
        text-transform: uppercase !important;
        color: #4a0000 !important;
    }

    /* 6. COLOR DE LOS DATOS (Para que no se vean claros sobre blanco) */
    [data-testid="stTable"] td {
        color: #000000 !important; /* Negro puro para los datos */
        background-color: white !important;
    }
    }
    </style>
""", unsafe_allow_html=True)

if "rol" not in st.session_state: st.session_state.rol = None

if st.session_state.rol is None:
    # 1. Título principal
    st.markdown('<p class="login-welcome"> ¡Tu talento es importante! :)</p>', unsafe_allow_html=True)
    
    # 2. LOGO (Nombre corregido a Logo_amarillo.png)
    col_logo1, col_logo2, col_logo3 = st.columns([1, 1.2, 1]) 
    with col_logo2:
        if os.path.exists("Logo_amarillo.png"):
            st.image("Logo_amarillo.png", use_container_width=True)
        else:
            # Mensaje de ayuda técnica por si acaso
            st.warning("No se encontró el archivo Logo_amarillo.png")

    # 3. Campos de entrada
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
    
    # --- SIDEBAR PERSONALIZADO ---
    with st.sidebar:
        # LOGO GUINDO: Alineado a la izquierda y tamaño reducido
        col_s1, col_s2 = st.columns([1, 0.5]) # La columna vacía a la derecha lo empuja a la izquierda
        with col_s1:
            if os.path.exists("Logo_guindo.png"):
                st.image("Logo_guindo.png", use_container_width=True)
            else:
                st.warning("Subir Logo_guindo.png")
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        # PANEL 1: GESTIÓN
        st.markdown("### 🛠️ MENÚ PRINCIPAL")
        m = st.radio("", ["🔍 Consulta", "➕ Registro", "📊 Nómina General"], key="menu_p")
        
        st.markdown("---")
        
        # PANEL 2: REPORTES
        st.markdown("### 📈 REPORTES")
        r = st.radio("", ["Vencimientos", "Vacaciones", "Estadísticas"], key="menu_r")
        
        st.markdown("---")
        if st.button("🚪 Cerrar Sesión"):
            st.session_state.rol = None
            st.rerun()

    # --- CONTENIDO PRINCIPAL (Área Guinda) ---
    # LOGO AMARILLO: Reducido a la mitad (usando columnas laterales más anchas)
    col_m1, col_m2, col_m3 = st.columns([1.5, 1, 1.5]) 
    with col_m2:
        if os.path.exists("Logo_amarillo.png"):
            st.image("Logo_amarillo.png", use_container_width=True) 
    
    # Espacio estético antes del título
    st.markdown("<br>", unsafe_allow_html=True)

    # Aquí sigue la lógica de m (Consulta, Registro, etc.)

    # CONTENIDO POR SECCIÓN
    if m == "🔍 Consulta":
        st.markdown("<h2 style='color: #FFD700;'>Búsqueda de Colaborador</h2>", unsafe_allow_html=True)
        dni_b = st.text_input("Ingrese DNI para consultar:").strip()
        
        if dni_b:
            pers = dfs["PERSONAL"][dfs["PERSONAL"]["dni"] == dni_b]
            if not pers.empty:
                nom_c = pers.iloc[0]["apellidos y nombres"]
                st.markdown(f"<h1 style='color: white; border-bottom: 2px solid #FFD700;'>👤 {nom_c}</h1>", unsafe_allow_html=True)
                st.header(f"👤 {nom_c}")
                t_noms = ["Datos Generales", "Exp. Laboral", "Form. Académica", "Investigación", "Datos Familiares", "Contratos", "Vacaciones", "Otros Beneficios", "Méritos/Demer.", "Evaluación", "Liquidaciones"]
                h_keys = ["DATOS GENERALES", "EXP. LABORAL", "FORM. ACADEMICA", "INVESTIGACION", "DATOS FAMILIARES", "CONTRATOS", "VACACIONES", "OTROS BENEFICIOS", "MERITOS Y DEMERITOS", "EVALUACION DEL DESEMPEÑO", "LIQUIDACIONES"]
                tabs = st.tabs(t_noms)

                for i, tab in enumerate(tabs):
                    h_name = h_keys[i]
                    with tab:
                        c_df = dfs[h_name][dfs[h_name]["dni"] == dni_b] if "dni" in dfs[h_name].columns else pd.DataFrame(columns=COLUMNAS[h_name])
                        
                        if h_name == "CONTRATOS":
                            if not c_df.empty:
                                st.download_button("📄 Certificado Word", gen_word(nom_c, dni_b, c_df), f"Cert_{dni_b}.docx")
                            
                            vst = c_df.copy()
                            vst.insert(0, "Sel", False)
                            ed = st.data_editor(vst, hide_index=True, use_container_width=True, key=f"ed_{h_name}")
                            sel = ed[ed["Sel"] == True]

                            if not es_lector:
                                col_a, col_b = st.columns(2)
                                with col_a:
                                    with st.expander("➕ Nuevo Contrato"):
                                        with st.form("f_add"):
                                            car = st.text_input("Cargo"); sue = st.number_input("Sueldo", 0.0)
                                            ini = st.date_input("Inicio"); fin = st.date_input("Fin")
                                            est_a = "ACTIVO" if fin >= date.today() else "CESADO"
                                            mot_a = st.selectbox("Motivo Cese", ["Vigente"] + MOTIVOS_CESE) if est_a == "CESADO" else "Vigente"
                                            if st.form_submit_button("Guardar"):
                                                nid = dfs[h_name]["id"].max() + 1 if not dfs[h_name].empty else 1
                                                new = {"id":nid, "dni":dni_b, "cargo":car, "sueldo":sue, "f_inicio":ini, "f_fin":fin, "estado":est_a, "motivo cese":mot_a}
                                                dfs[h_name] = pd.concat([dfs[h_name], pd.DataFrame([new])], ignore_index=True)
                                                save_data(dfs); st.rerun()
                                with col_b:
                                    with st.expander("📝 Editar/Eliminar Seleccionado"):
                                        if not sel.empty:
                                            with st.form("f_edit"):
                                                n_car = st.text_input("Cargo", value=sel.iloc[0]["cargo"])
                                                n_fin = st.date_input("Fin", value=pd.to_datetime(sel.iloc[0]["f_fin"]))
                                                est_e = "ACTIVO" if n_fin >= date.today() else "CESADO"
                                                mot_e = st.selectbox("Motivo Cese", MOTIVOS_CESE) if est_e == "CESADO" else "Vigente"
                                                if st.form_submit_button("Actualizar"):
                                                    idx = sel.index[0]
                                                    dfs[h_name].at[idx, "cargo"] = n_car
                                                    dfs[h_name].at[idx, "f_fin"] = n_fin
                                                    dfs[h_name].at[idx, "estado"] = est_e
                                                    dfs[h_name].at[idx, "motivo cese"] = mot_e
                                                    save_data(dfs); st.rerun()
                                            if st.button("🚨 Eliminar Fila"):
                                                dfs[h_name] = dfs[h_name].drop(sel.index)
                                                save_data(dfs); st.rerun()
                                        else: st.info("Selecciona una fila arriba")
                        else:
                            st.dataframe(c_df, use_container_width=True, hide_index=True)
                            if not es_lector:
                                with st.expander(f"➕ Registrar en {h_name}"):
                                    with st.form(f"f_{h_name}"):
                                        new_row = {"dni": dni_b}
                                        cols_f = [c for c in COLUMNAS[h_name] if c not in ["dni", "apellidos y nombres", "edad", "id"]]
                                        for col in cols_f: new_row[col] = st.text_input(col.title())
                                        if st.form_submit_button("Confirmar"):
                                            dfs[h_name] = pd.concat([dfs[h_name], pd.DataFrame([new_row])], ignore_index=True)
                                            save_data(dfs); st.rerun()
            else: st.error("No encontrado")

    elif m == "➕ Registro" and not es_lector:
        with st.form("reg_p"):
            st.write("### Alta de Nuevo Trabajador")
            d = st.text_input("DNI"); n = st.text_input("Nombres").upper(); l = st.text_input("Link File")
            if st.form_submit_button("Registrar"):
                if d and n:
                    dfs["PERSONAL"] = pd.concat([dfs["PERSONAL"], pd.DataFrame([{"dni":d, "apellidos y nombres":n, "link":l}])], ignore_index=True)
                    save_data(dfs); st.success("Registrado correctamente")

    elif m == "📊 Nómina General":
        st.dataframe(dfs["PERSONAL"], use_container_width=True, hide_index=True)



























